import sys
import json
import os
import pyautogui
import threading
from PyQt5.QtWidgets import QApplication, QMainWindow, QFileDialog, QLabel, QPushButton
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import QTimer, Qt
from pynput.mouse import Controller, Listener
from tool_image import Ui_MainWindow
from PIL import Image
from image_analyzer import ImageAnalyzer
from datetime import datetime
from PyQt5.QtWidgets import QMessageBox

CONFIG_FILE = "image_config.json"
IMAGE_FOLDER = "images"

class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.setWindowTitle("BetTool")

        self.image_label_1 = QLabel(self.frame_show_1)
        self.image_label_2 = QLabel(self.frame_show_2)
        self.mouse_label = QLabel(self.frame_show_mouse)
        self.mouse_label_2 = QLabel(self.frame_show_mouse_2)

        self.image_label_1.setGeometry(0, 0, self.frame_show_1.width(), self.frame_show_1.height())
        self.image_label_2.setGeometry(0, 0, self.frame_show_2.width(), self.frame_show_2.height())
        self.mouse_label.setGeometry(0, 0, 80, 80)
        self.mouse_label_2.setGeometry(0, 0, 80, 80)

        self.image_label_1.setScaledContents(True)
        self.image_label_2.setScaledContents(True)
        self.mouse_label.setScaledContents(True)
        self.mouse_label_2.setScaledContents(True)

        self.txt_show_result.setText("")

        self.btn_input_1.clicked.connect(self.load_image_1)
        self.pushButton_3.clicked.connect(self.load_image_2)
        self.btn_start.clicked.connect(self.start_tracking_mouse)

        # Add cancel button and connect its click event to cancel_processing method
        self.btn_cancel.clicked.connect(self.cancel_processing)

        self.load_saved_images()

        self.mouse_controller = Controller()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.track_mouse)

        self.listener = Listener(on_click=self.on_click)
        self.listener.start()
        self.check = False

        self.mouse_image_path = "mouse_image.png"
        if os.path.exists(self.mouse_image_path):
            self.mouse_label.setPixmap(QPixmap(self.mouse_image_path))

    def check_expiry_date(self):
        expiry_date = datetime(2025, 2, 3)
        current_date = datetime.now()

        if current_date > expiry_date:
            QMessageBox.critical(self, "Hết hạn", "Ứng dụng BetTool đã hết hạn")
            sys.exit()

    def load_image_1(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Chọn ảnh", "", "Images (*.png *.xpm *.jpg *.jpeg)")
        if file_name:
            self.save_and_display_image(file_name, "input1", self.image_label_1)

    def load_image_2(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Chọn ảnh", "", "Images (*.png *.xpm *.jpg *.jpeg)")
        if file_name:
            self.save_and_display_image(file_name, "input2", self.image_label_2)

    def save_and_display_image(self, file_name, image_name, label):
        if not os.path.exists(IMAGE_FOLDER):
            os.makedirs(IMAGE_FOLDER)
        image_path = os.path.join(IMAGE_FOLDER, image_name + os.path.splitext(file_name)[1])
        
        threading.Thread(target=self.save_image, args=(file_name, image_path)).start()
        
        label.setPixmap(QPixmap(image_path))
        self.save_image_path(image_name, image_path)

    def save_image(self, source_path, dest_path):
        image = Image.open(source_path)
        image.save(dest_path)

    def save_image_path(self, key, path):
        data = {}
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r") as f:
                data = json.load(f)

        data[key] = path

        with open(CONFIG_FILE, "w") as f:
            json.dump(data, f)

    def load_saved_images(self):
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r") as f:
                data = json.load(f)
                if "input1" in data and os.path.exists(data["input1"]):
                    self.image_label_1.setPixmap(QPixmap(data["input1"]))
                if "input2" in data and os.path.exists(data["input2"]):
                    self.image_label_2.setPixmap(QPixmap(data["input2"]))

    def start_tracking_mouse(self):
        self.check = True
        self.timer.start(100)

    def stop_tracking_mouse(self):
        self.timer.stop()
        
        screenshot_path = "mouse_screenshot.png"
        cropped_image_path = "cropped_mouse_screenshot.png"
        
        if os.path.exists(screenshot_path) and self.check:
            threading.Thread(target=self.crop_image, args=(screenshot_path, cropped_image_path)).start()
            self.check = False
        else:
            print(f"File {screenshot_path} not found.")
    def crop_image(self, screenshot_path, cropped_image_path):
        self.txt_show_result.setText("Đang phân tích...")

        analyzer = ImageAnalyzer()

        result_image = analyzer.booling_cursor(image_path=screenshot_path, margin_size=5)
        print("result_image", result_image)
        if result_image == 0:
            screenshot_path = "images/red_compare.png"
        else:
            screenshot_path = "images/blue_compare.png"

        self.mouse_label_2.setPixmap(QPixmap(screenshot_path))

        image_ref1 = "images/input1.png"
        image_ref2 = "images/input2.png"

        analyzer = ImageAnalyzer(
            image_ref1=image_ref1,
            image_ref2=image_ref2,
        )

        color_name, similarity = analyzer.process(screenshot_path)

        self.txt_show_result.setText(f"{str(similarity)} - {color_name}")

    def track_mouse(self):
        mouse_pos = self.mouse_controller.position

        region_size = 20
        half_region = region_size // 2

        left_x = mouse_pos[0] - half_region // 2
        top_y = mouse_pos[1] - half_region // 2

        screenshot = pyautogui.screenshot(region=(left_x, top_y, region_size, region_size))
        screenshot.save("mouse_screenshot.png")

        pixmap = QPixmap("mouse_screenshot.png")
        self.mouse_label.setPixmap(pixmap)

    def on_click(self, x, y, button, pressed):
        if pressed:
            self.stop_tracking_mouse()

    def cancel_processing(self):
        """Cancel all ongoing processes"""
        self.timer.stop()
        self.check = False
        self.txt_show_result.setText("Huỷ xử lý")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_win = MainWindow()
    main_win.check_expiry_date()
    main_win.show()
    sys.exit(app.exec())