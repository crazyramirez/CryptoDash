import sys
import os
import requests
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QGraphicsDropShadowEffect, QSpacerItem, QSizePolicy, QProgressDialog
from PyQt5.QtGui import QPixmap, QFont, QFontDatabase, QColor, QIcon, QPalette, QBrush
from PyQt5.QtCore import QTimer, Qt, QSize, QProcess, QEvent
from functools import partial
from datetime import datetime
from screeninfo import get_monitors, ScreenInfoError

# VARIABLES
BASE_PATH = os.path.dirname(os.path.realpath(__file__))
IMG_PATH = os.path.join(BASE_PATH, "images")
BACKGROUND_PATH = os.path.join(IMG_PATH, "backgrounds")
TOKEN_PATH = os.path.join(IMG_PATH, "tokens")
THUMB_PATH = os.path.join(IMG_PATH, "thumbs")
FONT_PATH = os.path.join(BASE_PATH, "fonts")
ICON_SIZE = 220
DATE_FORMAT = "%d-%m-%Y"
BUTTON_SIZE = 80

def get_screen_resolution():
    try:
        monitors = get_monitors()
        if monitors:
            for monitor in monitors:
                print(f"Monitor: {monitor.name}, Width: {monitor.width}, Height: {monitor.height}")
                return monitor.width, monitor.height
        else:
            raise ScreenInfoError("No monitors found")
    except ScreenInfoError as e:
        print(f"ScreenInfoError: {e}")
        # Return default resolution if no monitors are found
        return 800, 480

# Raspberry Pi Check
def is_raspberry_pi():
    try:
        with open('/proc/cpuinfo', 'r') as f:
            return any('Raspberry Pi' in line for line in f)
    except Exception as e:
        print(f"Not Raspberry")
    return False

# Binance Free Data API
def get_token_data(token_id):
    base_url = 'https://api.binance.com/api/v3/ticker/24hr'
    params = {
        'symbol': f'{token_id.upper()}USDT'
    }

    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()
        data_binance = response.json()

        data = {
            'price': float(data_binance['lastPrice']),
            '24h_change': float(data_binance['priceChangePercent']),
            'symbol': token_id.upper()
        }
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from Binance: {e}")
        data = {
            'price': 0,
            '24h_change': 0,
            'symbol': 'N/A'
        }
        
    return data

# Main App
class CryptoDashboard(QWidget):
    def __init__(self):
        super().__init__()
        self.current_token = 'Bitcoin'
        self.current_token_symbol = 'btc'
        self.current_background_index = 0
        self.width_res, self.height_res = get_screen_resolution()
        self.initUI()

    def initUI(self):
        
        # Progress Dialog
        self.progress_dialog = QProgressDialog("Loading...\nPlease Wait", None, 0, 0, self)
        self.progress_dialog.setWindowModality(Qt.WindowModal)
        self.progress_dialog.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.progress_dialog.setCancelButton(None)
        self.progress_dialog.hide()
        self.progress_dialog.cancel()
        self.progress_dialog.setStyleSheet("""
            QProgressDialog {
                background-color: #333333; 
                color: white; 
                border: none; 
                padding: 10px;
            }
            QLabel {
                background-color: #333333; 
                color: white;
                font-size: 18px;
                font-weight: bold;
            }
            QProgressBar {
                border: 1px solid #555555;
                border-radius: 5px;
                background: #777777;
                height: 10px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #222222; 
                width: 10px;
            }
        """)

        # Setup Window
        self.setWindowTitle('Crypto Dashboard')
        self.setGeometry(int(self.width_res/2 - 400), int(self.height_res/2 - 240), 800, 480)
        self.setStyleSheet('background-color: black;')
        self.set_background()
        
        # Remove navigation bar if on Raspberry Pi
        # self.setWindowFlag(Qt.FramelessWindowHint)

        # Load Montserrat fonts
        QFontDatabase.addApplicationFont(os.path.join(FONT_PATH, "Montserrat-ExtraBold.ttf"))
        QFontDatabase.addApplicationFont(os.path.join(FONT_PATH, "Montserrat-Regular.ttf"))

        # Main Layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(25, 25, 25, 25)  # Adjust margins
        # main_layout.setSpacing(20)  # Adjust spacing between elements

        # Button Layout with fixed size
        self.button_widget = QWidget()
        self.button_widget.setStyleSheet("background-color: transparent;")
        self.button_widget.setFixedSize(600, 80)
        self.button_layout = QHBoxLayout(self.button_widget)
        self.add_button(self.button_layout, 'Bitcoin', 'btc')
        self.add_button(self.button_layout, 'Ethereum', 'eth')
        self.add_button(self.button_layout, 'Cardano', 'ada')
        self.add_button(self.button_layout, 'Binance', 'bnb')
        self.add_button(self.button_layout, 'Solana', 'sol')

        # Create an additional layout to center the button_widget
        button_wrapper_layout = QHBoxLayout()
        button_wrapper_layout.addStretch(1)
        button_wrapper_layout.addWidget(self.button_widget)
        button_wrapper_layout.addStretch(1)

        # Info Layout Center Box
        centered_layout = QVBoxLayout()
        spacer_top = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)
        spacer_bottom = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)

        centered_layout.addItem(spacer_top)
        
        # Info Layout
        main_info_layout = QHBoxLayout()
        main_info_layout.addStretch(1)

        # Bitcoin Logo
        logo_container = QVBoxLayout()
        self.logo_label = QLabel(self)
        pixmap = QPixmap(os.path.join(TOKEN_PATH, "btc.png"))
        scaled_pixmap = pixmap.scaled(ICON_SIZE, ICON_SIZE, Qt.KeepAspectRatio)
        self.logo_label.setPixmap(scaled_pixmap)
        self.logo_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.logo_label.setStyleSheet("background-color: transparent;")
        self.set_shadow(self.logo_label, 'gray', 50)
        logo_container.addWidget(self.logo_label)
        main_info_layout.addLayout(logo_container)

        # Space between Logo and Text
        spacer_between = QSpacerItem(50, 0, QSizePolicy.Fixed, QSizePolicy.Minimum)
        main_info_layout.addItem(spacer_between)
        
        # Info Layout
        self.text_info_layout = QVBoxLayout()
        self.text_info_layout.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        # Name Label
        self.name_label = QLabel('Bitcoin (BTC)', self)
        self.name_label.setFont(QFont('Montserrat', 44, QFont.Bold))
        self.name_label.setStyleSheet("background-color: transparent; color: white;")
        self.text_info_layout.addWidget(self.name_label)
        self.set_shadow(self.name_label, 'gray', 10)
        shadow_effect = QGraphicsDropShadowEffect()
        shadow_effect.setBlurRadius(15)
        shadow_effect.setColor(QColor("#00FF00"))
        shadow_effect.setOffset(0, 0)
        self.name_label.setGraphicsEffect(shadow_effect)

        # Price Label
        self.price_label = QLabel('Price: $0', self)
        self.price_label.setFont(QFont('Montserrat', 36, QFont.Normal))
        self.price_label.setStyleSheet("background-color: transparent; color: white;")
        self.text_info_layout.addWidget(self.price_label)
        self.set_shadow(self.price_label, 'gray', 10)
        
        # 24h Change Label
        self.day_change_label = QLabel('24h Change: 0%', self)
        self.day_change_label.setFont(QFont('Montserrat', 28, QFont.Normal))
        self.day_change_label.setStyleSheet("background-color: transparent; color: white;")
        self.text_info_layout.addWidget(self.day_change_label)
        self.set_shadow(self.day_change_label, 'gray', 10)
        
        # Layouts Composition
        main_info_layout.addLayout(self.text_info_layout)
        main_info_layout.addStretch(1)
        
        centered_layout.addLayout(main_info_layout)
        centered_layout.addItem(spacer_bottom)

        # Date Time
        self.label_date = QLabel("", self)
        self.label_date.setStyleSheet("color: white; background-color: transparent; padding: 0px 30px")
        self.label_date.setAlignment(Qt.AlignLeft)
        self.label_date.setFont(QFont('Montserrat', 30, QFont.Bold))

        self.label_time = QLabel("", self)
        self.label_time.setStyleSheet("color: white; background-color: transparent; padding: 0px 30px")
        self.label_time.setAlignment(Qt.AlignRight)
        self.label_time.setFont(QFont('Montserrat', 30, QFont.Bold))

        self.date_time_layout = QHBoxLayout()
        self.date_time_layout.addWidget(self.label_date)
        self.date_time_layout.addWidget(self.label_time)
        
        width = self.width()
        height = self.height()

        # Settings Button
        self.settings_button = QLabel(self)
        pixmap = QPixmap(os.path.join(IMG_PATH, "settings.png"))
        self.settings_button.setPixmap(pixmap.scaled(30, 30, Qt.KeepAspectRatio))
        self.settings_button.setAlignment(Qt.AlignCenter | Qt.AlignTop)
        self.settings_button.mousePressEvent = self.settings_button_clicked
        self.set_shadow(self.settings_button, 'white', 10)
        self.settings_button.setGeometry(20, 20, 60, 60)
        self.settings_button.setStyleSheet("background-color: transparent; border: none;")

        # Setup Main Layout
        main_layout.addLayout(button_wrapper_layout)
        main_layout.addLayout(centered_layout)
        # main_layout.addStretch(1)
        main_layout.addLayout(self.date_time_layout)

        self.setLayout(main_layout)

        # Update Data Price every 1 min
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_data)
        self.timer.start(60000)

        # Update Data
        self.update_data()
        QTimer.singleShot(1000, self.update_data)

        # Set Background
        QTimer.singleShot(1000, self.set_background)
        QTimer.singleShot(4000, self.set_background)
        
        # Update Date Time
        self.update_time()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_time)
        self.timer.start(1000)
          
        app = QApplication.instance()
        app.installEventFilter(self)
      
    # Update Date Time
    def update_time(self):
        current_date = datetime.now().strftime(DATE_FORMAT)
        current_time = datetime.now().strftime('%H:%M:%S')
        self.label_date.setText(current_date)
        self.label_time.setText(current_time)
        
    # Set Single Background
    def set_background(self):
        palette = QPalette()
        pixmap = QPixmap(os.path.join(BACKGROUND_PATH, "img11.jpg"))
        scaled_pixmap = pixmap.scaled(self.size(), Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
        palette.setBrush(QPalette.Window, QBrush(scaled_pixmap))
        self.setPalette(palette)
        
    def resizeEvent(self, event):
        self.set_background()
        super().resizeEvent(event)

    # Add Buttons
    def add_button(self, layout, token_name, token_id):
        button = QPushButton(self)
        button.setIcon(QIcon(os.path.join(THUMB_PATH, f"{token_id}.png")))
        button.setIconSize(QSize(int(BUTTON_SIZE/1.5), int(BUTTON_SIZE/1.5)))
        button.setFixedSize(BUTTON_SIZE, BUTTON_SIZE)
        button.setStyleSheet("""
            QPushButton {
                background-color: transparent; 
                border: none; 
                padding: 0px; 
            }
            QPushButton:focus {
                outline: none;
            }
        """)
        button.clicked.connect(partial(self.change_token, token_name, token_id, button))
        layout.addWidget(button)

    # Change Token
    def change_token(self, token_name, token_id, button):
        print("Change token:", token_id)
        self.current_token = token_name
        self.current_token_symbol = token_id
        self.logo_label.setPixmap(QPixmap(os.path.join(TOKEN_PATH, f"{token_id}.png")).scaled(ICON_SIZE, ICON_SIZE, Qt.KeepAspectRatio))
        self.update_data()

    # Set Shadow
    def set_shadow(self, widget, color: str, blur_radius: int):
        shadow_effect = QGraphicsDropShadowEffect()
        shadow_effect.setBlurRadius(blur_radius)
        shadow_effect.setColor(QColor(color))
        shadow_effect.setOffset(0, 0)
        widget.setGraphicsEffect(shadow_effect)
        
    # Update Data
    def update_data(self):        
        data = get_token_data(self.current_token_symbol)
        price = data['price']
        day_change = data['24h_change']

        # Name and Symbol Update
        self.name_label.setText(f'{self.current_token} ({self.current_token_symbol.upper()})')
        
        # Price Update
        self.price_label.setText(f'Price: {price:,.2f} $')

        # 24h Change Label Update
        color = "green" if day_change >= 0 else "red"
        self.day_change_label.setText(f'24h Change: <span style="color:{color};">{day_change:.2f}%</span>')

    def settings_button_clicked(self, event):
        self.settings_button.setEnabled(False)
        self.progress_dialog.show()
        self.progress_dialog.raise_()  # Elevar al frente
        self.progress_dialog.activateWindow()  # Activar ventana
        print("Settings button clicked")
        
        self.process = QProcess(self)
        try:
            script_path = os.path.join(BASE_PATH, "network.py")
            command = ["sudo" if is_raspberry_pi() else "python3", "python3" if is_raspberry_pi() else "python", script_path]
            self.process.start(command[0], command[1:])
            print("Network script started")
        except Exception as e:
            print(f"Error opening network script: {str(e)}")

    def eventFilter(self, obj, event):
        if event.type() == QEvent.ApplicationActivate:
            self.progress_dialog.hide()
            self.settings_button.setEnabled(True)
        return super().eventFilter(obj, event)

# Main
if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = CryptoDashboard()
    if is_raspberry_pi():
        ex.showFullScreen()
    else:
        ex.show()
    sys.exit(app.exec_())
