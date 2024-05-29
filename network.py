import sys
import os
import subprocess
import socket
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QPushButton, QLabel, QListWidget, QLineEdit, QMessageBox, QGridLayout)
from PyQt5.QtGui import QFont, QFontDatabase, QPainter, QImage
from PyQt5.QtCore import Qt, QTimer
from pywifi import PyWiFi, const, Profile
import json
from screeninfo import get_monitors, ScreenInfoError

# Constants and global variables
BASE_PATH = os.path.dirname(os.path.realpath(__file__))
WIFI_CONFIG_FILE = os.path.join(BASE_PATH, "wifi_config.json")
WIFI_INTERFACE_INDEX = 1

def get_screen_resolution():
    """Returns the resolution of the primary monitor."""
    try:
        monitors = get_monitors()
        if monitors:
            monitor = monitors[0]
            return monitor.width, monitor.height
    except ScreenInfoError as e:
        print(f"ScreenInfoError: {e}")
    return 720, 480

def configure_wifi(ssid, password):
    config_lines = [
        'ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev',
        'update_config=1',
        'country=ES',
        '\n',
        'network={',
        '\tssid="{}"'.format(ssid),
        '\tpsk="{}"'.format(password),
        '}'
        ]
    config = '\n'.join(config_lines)
    
    # Give access and writing permissions. May have to do this manually beforehand
    os.popen("sudo chmod a+w /etc/wpa_supplicant/wpa_supplicant.conf")
    
    # Writing to file
    with open("/etc/wpa_supplicant/wpa_supplicant.conf", "w") as wifi:
        wifi.write(config)
    
    print("Wifi config added. Refreshing configs")
    # Refresh configs
    os.popen("sudo wpa_cli -i wlan0 reconfigure")

width, height = get_screen_resolution()
os.environ['XDG_RUNTIME_DIR'] = "/tmp/runtime-root"

class WiFiManager(QWidget):
    def __init__(self):
        super().__init__()
        self.caps_lock_enabled = False
        self.is_special = False
        self.selected_input = None
        self.timer = QTimer()
        self.initUI()

    def initUI(self):
        self.setWindowTitle('WiFi Manager')
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setStyleSheet("background-color: gray; color: white;")
        QFontDatabase.addApplicationFont(os.path.join(BASE_PATH, "fonts/Montserrat-Regular.ttf"))

        layout = QVBoxLayout(self)

        self.status_label = self.create_label('SCANNING NETWORKS')
        self.network_list = self.create_list_widget()
        self.password_input = self.create_line_edit('Enter WiFi password', self.input_focused)
        self.selected_input = self.password_input
        self.password_input.setStyleSheet("color: white; border: none; padding: 5px; background-color: rgba(0,0,0,180);")
        self.connect_button = self.create_button('CONNECT', self.connect_to_network, "green")
        self.close_button = self.create_button('CLOSE', self.close_app, "rgb(60,60,60)")

        self.setup_layout(layout)
        self.adjust_elements_to_screen()
        self.showFullScreen()

        self.refresh_networks()
        QTimer.singleShot(2000, self.refresh_networks)

        # Conectar el evento de selección de la lista al método para enfocar el campo de contraseña
        self.network_list.itemSelectionChanged.connect(self.on_network_selected)

    def create_line_edit(self, placeholder, focus_event_handler):
        line_edit = QLineEdit()
        line_edit.setPlaceholderText(placeholder)
        line_edit.setStyleSheet("color: white; border: none; padding: 5px; background-color: rgba(0,0,0,180);")
        line_edit.setFont(QFont('Montserrat Regular', 14))
        line_edit.focusInEvent = lambda event: focus_event_handler(line_edit)
        return line_edit

    def create_button(self, text, click_event_handler, bg_color="rgb(40,80,190)"):
        button = QPushButton(text)
        button.setStyleSheet(f"color: white; border: none; border-radius: 2px; padding: 8px; background-color: {bg_color}; font-weight: bold;")
        button.setFont(QFont('Montserrat Regular', 12))
        button.clicked.connect(click_event_handler)
        return button

    def create_label(self, text):
        label = QLabel(text)
        # label.setStyleSheet("color: white; background-color: rgba(0,0,0,180); height: 20px;")
        label.setAlignment(Qt.AlignCenter)
        # label.setContentsMargins(0, 5, 0, 5) 
        label.setFont(QFont('Montserrat Regular', 15))
        return label

    def create_list_widget(self):
        list_widget = QListWidget()
        list_widget.setStyleSheet("color: white; border: none; height: 40px; background-color: rgba(0,0,0,180); padding: 5px;")
        list_widget.setFont(QFont('Montserrat Regular', 12))
        return list_widget

    def setup_layout(self, layout):

        layout.addWidget(self.status_label)
        layout.addWidget(self.network_list)
        layout.addWidget(self.password_input)

        buttons_layout = QGridLayout()
        buttons_layout.addWidget(self.close_button, 0, 0)
        buttons_layout.addWidget(self.connect_button, 0, 1)
        layout.addLayout(buttons_layout)

        self.setLayout(layout)
        
        self.keyboard_layout = QGridLayout()
        self.add_keys()
        layout.addLayout(self.keyboard_layout)

    def add_keys(self):
        self.normal_keys = [
            ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0'],
            ['q', 'w', 'e', 'r', 't', 'y', 'u', 'i', 'o', 'p'],
            ['a', 's', 'd', 'f', 'g', 'h', 'j', 'k', 'l', '*'],
            ['z', 'x', 'c', 'v', 'b', 'n', 'm', ',', '.', '+'],
            ['-', '_', '=', '$', '€', '/', '%', '#', '(', ')'],
            ['@', 'capsL', 'Space', 'Del', 'Clear', 'Special', 'Enter']
        ]
        self.special_keys = [
            ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0'],
            ['q', 'w', 'e', 'r', 't', 'y', 'u', 'i', 'o', 'p'],
            ['á', 'é', 'í', 'ó', 'ú', 'ü', 'ñ', 'à', 'è', 'ì'],
            ['â', 'ê', 'î', 'ô', 'û', 'ç', 'ä', 'ë', 'ï', 'ö'],
            ['-', '_', '=', '$', '€', '/', '%', '#', '(', ')'],
            ['@', 'CapsL', 'Space', 'Del', 'Clear', 'Normal', 'Enter']
        ]
        self.load_keys(self.normal_keys)

    def load_keys(self, keys):
        self.keyboard_layout.setParent(None)
        self.keyboard_layout = QGridLayout()
        for i, row in enumerate(keys):
            for j, key in enumerate(row):
                button = QPushButton(key)
                button.setStyleSheet("color: white; background-color: rgb(30,30,30); border: none; font-weight: bold; border-radius: 5px; padding: 8px;")
                button.setFont(QFont('Montserrat Regular', 12))
                button.clicked.connect(lambda ch, key=key: self.key_pressed(key))
                self.keyboard_layout.addWidget(button, i, j)

    def key_pressed(self, key):
        if key == 'Space':
            self.selected_input.insert(' ')
        elif key == 'Del':
            self.selected_input.backspace()
        elif key == 'Clear':
            self.selected_input.clear()
        elif key == 'Enter':
            self.connect_to_network()
        elif key == 'capsL':
            self.toggle_caps_lock()
        elif key in ['Special', 'Normal']:
            self.toggle_special_chars()
        else:
            self.selected_input.insert(key.upper() if self.caps_lock_enabled else key)

    def toggle_special_chars(self):
        self.is_special = not self.is_special
        self.load_keys(self.special_keys if self.is_special else self.normal_keys)

    def toggle_caps_lock(self):
        self.caps_lock_enabled = not self.caps_lock_enabled
        self.update_keys_case()

    def update_keys_case(self):
        for i in range(self.keyboard_layout.count()):
            button = self.keyboard_layout.itemAt(i).widget()
            key = button.text()
            if key.isalpha():
                button.setText(key.upper() if self.caps_lock_enabled else key.lower())

    def adjust_elements_to_screen(self):
        self.setGeometry(0, 0, width, height)

    def paintEvent(self, event):
        painter = QPainter(self)
        image = QImage(os.path.join(BASE_PATH, "images/backgrounds/img11.jpg"))
        painter.drawImage(self.rect(), image)

    def input_focused(self, input_widget):
        self.password_input.setStyleSheet("color: white; border: none; padding: 5px; background-color: rgba(0,0,0,180);")
        self.selected_input = input_widget
        self.selected_input.setStyleSheet("color: #ADE4F7; border: none; padding: 5px; background-color: rgba(0,0,0,180);")

    def refresh_networks(self):
        networks = self.scan_wifi_networks()
        self.network_list.clear()
        self.network_list.addItems(networks)
        self.check_connection()

    def scan_wifi_networks(self):
        wifi = PyWiFi()
        iface = wifi.interfaces()[WIFI_INTERFACE_INDEX]
        iface.scan()
        result = iface.scan_results()
        return [network.ssid for network in result]

    def on_network_selected(self):
        self.password_input.setFocus()

    def connect_to_network(self):
        selected_items = self.network_list.selectedItems()
        if selected_items:
            ssid = selected_items[0].text()
            password = self.password_input.text()
            if password:
                self.attempt_connection(ssid, password)
            else:
                self.show_alert_message("Please provide password.", QMessageBox.Warning)
        else:
            self.show_alert_message("Please select a network from the list.", QMessageBox.Warning)

    def attempt_connection(self, ssid, password):
        wifi = PyWiFi()
        iface = wifi.interfaces()[WIFI_INTERFACE_INDEX]
        profile = Profile()
        profile.ssid = ssid
        profile.auth = const.AUTH_ALG_OPEN
        profile.akm.append(const.AKM_TYPE_WPA2PSK)
        profile.cipher = const.CIPHER_TYPE_CCMP
        profile.key = password
        iface.remove_all_network_profiles()
        tmp_profile = iface.add_network_profile(profile)
        iface.connect(tmp_profile)
        self.show_alert_message(f'Attempting to connect to {ssid}...', QMessageBox.Information)
        QTimer.singleShot(1000, self.check_connection)
        QTimer.singleShot(5000, self.check_connection)

    def check_connection(self):
        wifi = PyWiFi()
        iface = wifi.interfaces()[WIFI_INTERFACE_INDEX]
        status = iface.status()
        if status == const.IFACE_CONNECTED:
            connected_network = self.get_connected_wifi_ssid()
            ip_address = self.get_ip_address()
            self.status_label.setStyleSheet("color: rgb(0,255,0); background-color: rgba(0,0,0,0);")
            self.status_label.setText(f"WIFI CONNECTED TO {connected_network}")
            # Save the successful connection
            selected_items = self.network_list.selectedItems()
            if selected_items:
                ssid = selected_items[0].text()
                password = self.password_input.text()
                configure_wifi(ssid, password)
        else:
            self.status_label.setStyleSheet("color: red; background-color: rgba(0,0,0,0);")
            self.status_label.setText("WIFI NOT CONNECTED")

    def get_ip_address(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(0)
            s.connect(('8.8.8.8', 1))
            ip_address = s.getsockname()[0]
            s.close()
            return ip_address
        except Exception as e:
            print(f"Error getting IP address: {e}")
            return "0.0.0.0"

    def get_connected_wifi_ssid(self):
        try:
            result = subprocess.run(['iwgetid', '-r'], capture_output=True, text=True)
            return result.stdout.strip() if result.returncode == 0 else "Unknown"
        except Exception as e:
            print(f"Error getting connected SSID: {e}")
            return "Unknown"

    def close_app(self):
        QApplication.quit()

    def show_alert_message(self, message, icon):
        msg_box = QMessageBox()
        msg_box.setIcon(icon)
        msg_box.setStyleSheet("""
            QLabel{color: white}
            QPushButton{color: white; background-color: black}
            QMessageBox{background-color: black}
        """)
        msg_box.setWindowFlags(Qt.FramelessWindowHint | Qt.CustomizeWindowHint)
        msg_box.setMinimumSize(400, 200)
        msg_box.setFont(QFont('Montserrat Regular', 12, QFont.Bold))
        msg_box.setText(message)
        msg_box.exec()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = WiFiManager()
    sys.exit(app.exec_())
