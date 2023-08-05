#!/usr/bin/env python3

import yaml
from yaml.loader import SafeLoader
from smtplib import SMTP
import os
import pwd
import grp
import socket
from email.message import EmailMessage

class Notify:
    def __init__(self, name):
        self.name = name
        self.email = EmailMessage()
        
    def set_notification_settings(self, notification_settings):
        self.notification_settings = notification_settings

    def set_notification_message(self, message):
        self.email.set_content(message)

    def set_notification_subject(self, subject):
        self.email['Subject'] = subject
    
    def send_notifiction(self):

        if self.notification_settings is None:
            print("SMTP settings are empty you need to provide the settings in conf/notification.yaml")
            exit(1)
        else:
            self.email['To'] = self.notification_settings['email_to']
            self.email['From'] = "monitorbox@" + socket.gethostname()

            with SMTP(self.notification_settings['sendmail_host']) as smtp:
                # print()
                # smtp.set_debuglevel(1)
                smtp.send_message(self.email)
                smtp.quit()

class FileMonitor:
    def __init__(self, file_name, settings):
        self.file_name = file_name
        self.settings = settings
        self.status = "okay"
        self.message = ""
        self.checked = False

    def check(self):
        
        if os.path.isfile(self.file_name):

            self.exists = True
            self.file_stats = os.stat(self.file_name)

        else:

            self.exists = False
            self.message = "File " + self.file_name + " doesn't not exist."
            self.status = "failed"

        if self.exists:

            if self.file_stats.st_size == 0:

                self.zero_bytes = True
                self.message = "File " + self.file_name + " is 0 bytes."
                self.status = "failed"

        if self.settings['size_limit']:

            if self.settings['size_limit'] > 0:

                if self.file_stats.st_size / (1024 * 1024) > self.settings['size_limit']:

                    self.size_limit_reached = True
                    self.message = "File " + self.file_name + " is " + self.file_status.st_size / (1024 * 1024) + "which is greater than the limit of " + self.settings['size_limit']
                    self.status = "failed"

        if self.settings['user']:

            if pwd.getpwuid(self.file_stats.st_uid).pw_name != self.settings['user']:

                self.incorrect_user = True
                self.message = "File " + self.file_name + " is owned by " + pwd.getpwuid(self.file_stats.st_uid).pw_name + " and expecting it to be owned by " + self.settings['user']
                self.status = "failed"
            
        if self.settings['group']:
        
            if grp.getgrgid(self.file_stats.st_gid).gr_name != self.settings['group']:

                self.incorrect_group = True
                self.message = "File " + self.file_name + " has group " + grp.getgrgid(self.file_stats.st_gid).gr_name + " and it should be " + self.settings["group"]
                self.status = "failed"

        if str(self.settings['mode']):

            if str(self.file_stats.st_mode) != self.settings['mode']:

                self.incorrect_mode = True
                self.message = "File " + self.file_name + " has mode " + str(self.file_stats.st_mode) + " but should be " + self.settings['mode']
                self.status = "failed"

        self.checked = True
        return True

class PortMonitor():
    def __init__(self, name, settings):
        self.name = name
        self.settings = settings
        self.message = ""
        self.open = False
        self.status = "unknown"
        self.checked = False

    def check(self):

        if self.settings:

            if self.settings['protocol'] == 'tcp':
                tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                if self.settings['timeout']:
                    tcp_socket.settimeout(self.settings['timeout'])
                else:
                    tcp_socket.settimeout(1)

                try:
                    tcp_socket.connect((self.settings['ip'], int(self.settings['port'])))
                    tcp_socket.shutdown(socket.SHUT_RDWR)
                    self.open = True
                    self.status = "okay"
                except Exception as e:
                    print(e)
                    self.status = "failed"
                    self.message = "ip " + self.settings['ip'] + " " + self.settings['protocol'] + " port " + str(self.settings['port']) + " is closed."
                finally:
                    tcp_socket.close()

            elif self.settings['protocol'] == 'udp':
                udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

                udp_socket.sendto("PING".encode(), (self.settings['ip'], self.settings['port']))
                
                response = udp_socket.recv(1024)

                if not response:
                    self.open = False
                    self.status = "failed"
                    self.message = "ip " + self.settings['ip'] + " " + self.settings['protocol'] + " port " + str(self.settings['port']) + " is closed."
                else:
                    self.open = True
                    self.status = "okay"
            else:
                self.status = 'unsupported protocol'
                self.open = False

        self.checked = True
        return True





    
# Open notificiation configuration file
with open('config/notification.yaml') as f:
    notification_settings_config = yaml.load(f, Loader=SafeLoader)

# Open File monitor configuration file
with open('config/file.yaml') as f:
    file_monitor_config = yaml.load(f, Loader=SafeLoader)

# Open port monitor configuration file
with open('config/port.yaml') as f:
    port_monitor_config = yaml.load(f, Loader=SafeLoader)

# Open disk usage monitor configuration file
with open('config/disk_usage.yaml') as f:
    disk_usage_monitor_config = yaml.load(f, Loader=SafeLoader)

print("MonitorBox Client")
print("Version 0.0.1")

print("Host " + socket.gethostname() + "\n")

print("-File Status-")

notification_object = Notify('file_alert')
notification_object.set_notification_settings(notification_settings_config)
notification_object.set_notification_subject(socket.gethostname() + " Has A Monitorbox Alert")

for file_monitor in file_monitor_config['files']:
    file_name = file_monitor['name']
    
    file_monitor_object = FileMonitor(file_name, file_monitor)
    file_monitor_object.check()

    notification_object.set_notification_message(file_monitor_object.message)

    if file_monitor_object.status == "failed":
        notification_object.send_notifiction()
    
    print(file_monitor_object.file_name + " : " + file_monitor_object.status)

print()
print("-Port Status-")

for port_monitor in port_monitor_config['ports']:
    connection_name = port_monitor['protocol'] + " " + port_monitor['ip'] + " port " + str(port_monitor['port'])

    port_monitor_object = PortMonitor(connection_name, port_monitor)
    port_monitor_object.check()

    notification_object.set_notification_message(port_monitor_object.message)

    if port_monitor_object.status == "failed":
        notification_object.send_notifiction()

    print(connection_name + " : " + port_monitor_object.status)

