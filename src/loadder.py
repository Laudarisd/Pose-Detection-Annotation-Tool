import sys
import os
import csv
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QLabel, QWidget, QPushButton, QFileDialog, QTableWidget, QTableWidgetItem, QGraphicsView, QGraphicsScene, QShortcut, QListWidget, QGraphicsPixmapItem, QGraphicsEllipseItem, QHeaderView, QGraphicsLineItem, QMessageBox, QSplitter, QMenu
from PyQt5.QtCore import Qt, QPointF, QRectF, QEvent
from PyQt5.QtGui import QPixmap, QPen, QColor, QKeySequence, QCursor, QPainter, QWheelEvent

class Loadder: 
    def upload_folder(self):
            folder = QFileDialog.getExistingDirectory(self, "Select Folder")
            if folder:
                self.imageFiles = [os.path.join(folder, file) for file in os.listdir(folder) if file.lower().endswith(('png', 'jpg', 'jpeg'))]
                if self.imageFiles:
                    self.currentImageIndex = 0
                    self.fileListWidget.clear()
                    for file in self.imageFiles:
                        self.fileListWidget.addItem(os.path.basename(file))
                    self.load_image()

    def load_image(self):
        self.currentImageIndex = self.fileListWidget.currentRow()
        if 0 <= self.currentImageIndex < len(self.imageFiles):
            self.pixmap = QPixmap(self.imageFiles[self.currentImageIndex])
            self.scene.clear()
            self.pixmapItem = QGraphicsPixmapItem(self.pixmap)
            self.scene.addItem(self.pixmapItem)
            self.fit_to_screen()
            self.lines.clear()
            self.points.clear()
            self.actions.clear()  # Clear actions when a new image is loaded
            
            # Try to load existing annotations
            annotation_exists = self.load_data()
            if annotation_exists:
                #self.update_scene()  # Update scene to show loaded annotations
                self.drawer.update_scene()  # Update scene to show loaded annotations

            
            self.update_data_table()
            self.edited = False  # Reset edited flag when loading a new image

    def load_data(self):
        csv_file = os.path.join('csv_data', os.path.splitext(os.path.basename(self.imageFiles[self.currentImageIndex]))[0] + ".csv")
        
        if os.path.exists(csv_file):
            try:
                with open(csv_file, 'r') as f:
                    reader = csv.DictReader(f)
                    
                    # Ensure required columns exist
                    if not {"Start X", "Start Y", "End X", "End Y"}.issubset(reader.fieldnames):
                        print("CSV file is missing required columns.")
                        return False
                    
                    # Clear existing data
                    self.lines.clear()
                    self.points.clear()
                    
                    for row in reader:
                        start_point = QPointF(int(float(row["Start X"])), int(float(row["Start Y"])))
                        end_point = QPointF(int(float(row["End X"])), int(float(row["End Y"])))
                        class_name = row.get("Class", "None")  # Default to "None" if class is not provided
                        
                        # Add start point
                        start_item = self.scene.addEllipse(
                            start_point.x() - self.pointSize / 2,
                            start_point.y() - self.pointSize / 2,
                            self.pointSize, self.pointSize,
                            QPen(Qt.blue), QColor(Qt.blue)
                        )
                        self.points.append({"point": start_point, "item": start_item, "class": class_name})
                        
                        # Add end point
                        end_item = self.scene.addEllipse(
                            end_point.x() - self.pointSize / 2,
                            end_point.y() - self.pointSize / 2,
                            self.pointSize, self.pointSize,
                            QPen(Qt.blue), QColor(Qt.blue)
                        )
                        self.points.append({"point": end_point, "item": end_item, "class": class_name})
                        
                        # Add line as a dictionary with class info
                        self.lines.append({"start": start_point, "end": end_point, "class": class_name})
                    
                    return True
            except Exception as e:
                print(f"Error loading annotation file: {e}")
                return False
        return False
