import sys
import json
import os
import pyautogui
import threading
from PyQt5.QtWidgets import QApplication, QMainWindow, QFileDialog, QLabel, QPushButton
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import QTimer, Qt, QSize
from pynput.mouse import Controller, Listener
from tool_image import Ui_MainWindow
from PIL import Image
from image_analyzer import ImageAnalyzer
from image_analyzer_v2 import ImageAnalyzerv2
from datetime import datetime
from PyQt5.QtWidgets import QMessageBox, QRubberBand, QVBoxLayout
import random
import time
from shutil import copy2
from PyQt5.QtWidgets import QRubberBand
from PyQt5.QtCore import QRect, QPoint
import pyautogui
import cv2
import shutil
import numpy as np

CONFIG_FILE = "image_config.json"
IMAGE_FOLDER = "images"

if not os.path.exists("red_image"):
    os.makedirs("red_image")
if not os.path.exists("blue_image"):
    os.makedirs("blue_image")

class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.setWindowTitle("BetTool")
        self.adjusted_similarity_red = None
        self.color_name_red = None
        self.adjusted_similarity_blue = None
        self.color_name_blue = None
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

        self.btn_game.clicked.connect(self.start_selection)
        self.rubberBand = QRubberBand(QRubberBand.Rectangle, self)
        self.origin = QPoint()

        self.txt_show_result.setText("")
        self.txt_show_result_2.setText("")

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

    def start_selection(self):
        self.setWindowOpacity(0.3)
        self.setMouseTracking(True)
        self.showFullScreen()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.origin = event.pos()
            self.rubberBand.setGeometry(QRect(self.origin, QSize()))
            self.rubberBand.show()

    def mouseMoveEvent(self, event):
        if not self.origin.isNull():
            self.rubberBand.setGeometry(QRect(self.origin, event.pos()).normalized())

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.rubberBand.hide()
            self.setWindowOpacity(1.0)
            self.setMouseTracking(False)
            self.showNormal()
            self.take_screenshot(self.rubberBand.geometry())

    def take_screenshot(self, rect):
        screen = QApplication.primaryScreen()
        screenshot = screen.grabWindow(0, rect.x(), rect.y(), rect.width(), rect.height())

        # Đường dẫn tệp
        folder_path = 'images_region'
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
        
        # file_path_2 = os.path.join(folder_path, 'selected_region_2.png')
        # file_path_1 = os.path.join(folder_path, 'selected_region_1.png')
        
        # # Kiểm tra và xóa tệp cũ nếu tồn tại
        # if os.path.exists(file_path_1):
        #     os.remove(file_path_1)
        
        # # Đổi tên tệp
        # if os.path.exists(file_path_2):
        #     os.rename(file_path_2, file_path_1)
        
        # # Lưu ảnh mới
        # screenshot.save(file_path_2)
        # print(f'Screenshot saved to {file_path_2}')

        coordinates = {
            "top_left": {"x": rect.x(), "y": rect.y()},
            "top_right": {"x": rect.x() + rect.width(), "y": rect.y()},
            "bottom_left": {"x": rect.x(), "y": rect.y() + rect.height()},
            "bottom_right": {"x": rect.x() + rect.width(), "y": rect.y() + rect.height()}
        }
        coordinates_path = os.path.join(folder_path, 'coordinates.json')
        with open(coordinates_path, 'w') as f:
            json.dump(coordinates, f, indent=4)
        print(f'Coordinates saved to {coordinates_path}')

    def check_expiry_date(self):
        expiry_date = datetime(2025, 3, 1)
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
        
        self.save_image(file_name, image_path)
        
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
        try:
            self.txt_show_result.setText("Chọn thêm hình xanh")
            self.txt_show_result_2.setText("Đang phân tích...")



            # Load coordinates from JSON file
            coordinates_path = "images_region/coordinates.json"
            with open(coordinates_path, 'r') as f:
                coordinates = json.load(f)

            # Get the coordinates
            top_left = coordinates["top_left"]
            bottom_right = coordinates["bottom_right"]

            # Tính width và height
            width = bottom_right["x"] - top_left["x"]
            height = bottom_right["y"] - top_left["y"]


            # Crop the image
            screenshot = pyautogui.screenshot(region=(top_left["x"], top_left["y"], width, height))     
            # Đường dẫn tệp
            folder_path = 'images_region'
            if not os.path.exists(folder_path):
                os.makedirs(folder_path)
            
            analyzer = ImageAnalyzerv2(min_similarity=0.5, image_ref1='images/blue_cursor.png', image_ref2='images/red_cursor.png')
            
            result_image = analyzer.booling_cursor(image_path=screenshot_path, margin_size=0)

            image_ref1 = "images/input1.png"
            image_ref2 = "images/input2.png"

            if result_image == 0:
                file_path = os.path.join(folder_path, 'selected_region_red.png')
                screenshot.save(file_path)
                self.mouse_label_2.setPixmap(QPixmap('images/red1.png'))

            elif result_image == 1:
                file_path = os.path.join(folder_path, 'selected_region_blue.png')
                screenshot.save(file_path)
                self.mouse_label_2.setPixmap(QPixmap('images/blue1.png'))
            else:
                screenshot_path = ""
            image1 = os.path.join(folder_path, 'selected_region_red.png')
            image2 = os.path.join(folder_path, 'selected_region_blue.png')
            img1 = cv2.imread(image1)
            img2 = cv2.imread(image2)

            # Định nghĩa thư mục output
            cell_output_dir = "image_cells"
            diff_output_dir = "cell_differences"

            # Xóa thư mục nếu đã tồn tại và tạo mới
            for folder in [cell_output_dir, diff_output_dir]:
                if os.path.exists(folder):
                    shutil.rmtree(folder)  # Xóa toàn bộ thư mục
                os.makedirs(folder)  # Tạo lại thư mục mới

            os.makedirs(cell_output_dir, exist_ok=True)
            os.makedirs(diff_output_dir, exist_ok=True)

            def extract_cells(image):
                """Phát hiện và cắt các ô từ hình ảnh."""
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                ret, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
                contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

                cells = []
                for c in contours:
                    x, y, w, h = cv2.boundingRect(c)
                    if (4 < w < 200) and (4 < h < 200):  # Giới hạn kích thước ô
                        cell = image[y:y+h, x:x+w]  # Cắt ô
                        cells.append((x, y, cell))  # Lưu vị trí và ảnh ô

                # Sắp xếp theo vị trí x, y để ghép đúng thứ tự
                cells.sort(key=lambda c: (c[0], c[1]))  
                return cells

            # Cắt và lưu tất cả ô từ hai ảnh
            cells1 = extract_cells(img1)
            cells2 = extract_cells(img2)

            # Đảm bảo số lượng ô của hai ảnh bằng nhau
            min_cells = min(len(cells1), len(cells2))
            cells1 = cells1[:min_cells]  
            cells2 = cells2[:min_cells]  

            # Lưu tất cả các ô đã cắt theo thứ tự đúng
            for i, ((x1, y1, cell1), (x2, y2, cell2)) in enumerate(zip(cells1, cells2)):
                cv2.imwrite(f"{cell_output_dir}/image1_cell_{i+1}.png", cell1)
                cv2.imwrite(f"{cell_output_dir}/image2_cell_{i+1}.png", cell2)

                # So sánh các ô và lưu nếu có sự khác biệt
                if cell1.shape == cell2.shape:  
                    diff = cv2.absdiff(cv2.cvtColor(cell1, cv2.COLOR_BGR2GRAY),
                                    cv2.cvtColor(cell2, cv2.COLOR_BGR2GRAY))
                    _, diff_thresh = cv2.threshold(diff, 30, 255, cv2.THRESH_BINARY)

                    if np.any(diff_thresh):  
                        cv2.imwrite(f"{diff_output_dir}/difference_image1.png", cell1)
                        cv2.imwrite(f"{diff_output_dir}/difference_image2.png", cell2)

            result = ImageAnalyzerv2(
                image_ref1=image_ref1,
                image_ref2=image_ref2,
            )
            color_name_1, similarity_1 = result.process(os.path.join('cell_differences', 'difference_image1.png'))
            color_name_2, similarity_2 = result.process(os.path.join('cell_differences', 'difference_image2.png'))
            adjusted_similarity_1 = round(similarity_1,3)
            adjusted_similarity_2 = round(similarity_2,3)
            self.txt_show_result.setText(f"{str(adjusted_similarity_1)} - {color_name_1}")
            self.txt_show_result_2.setText(f"{str(adjusted_similarity_2)} - {color_name_2}")

        except Exception as e:
            print("errror",e)
            self.txt_show_result.setText("Ảnh nhập không hợp lệ")

    def random_sleep(self):
        random.seed(time.time())
        return round(random.uniform(0.5, 2), 3)
    def track_mouse(self):
        mouse_pos = self.mouse_controller.position

        region_size = 14
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