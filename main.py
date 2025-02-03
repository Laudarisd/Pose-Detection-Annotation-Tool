import sys
import os
import csv
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QLabel, QWidget, QPushButton, QFileDialog, QTableWidget, QTableWidgetItem, QGraphicsView, QGraphicsScene, QShortcut, QListWidget, QGraphicsPixmapItem, QGraphicsEllipseItem, QHeaderView, QGraphicsLineItem, QMessageBox, QSplitter, QMenu
from PyQt5.QtCore import Qt, QPointF, QRectF, QEvent
from PyQt5.QtGui import QPixmap, QPen, QColor, QKeySequence, QCursor, QPainter, QWheelEvent
from src.loadder import Loadder
from src.ui_setup import UISetup
from src.drawer import Drawer
from src.edit_tools import EditTools


class AnnotationTool(QMainWindow, Loadder, UISetup, Drawer, EditTools):
    def __init__(self):
        super().__init__()
        self.setup_ui()
        self.setup_left_panel()
        self.setup_mid_panel()
        self.setup_right_panel()

        # Variables for drawing
        self.drawing = False
        self.editing = False
        self.zooming = False
        self.startPoint = None
        self.endPoint = None
        self.currentLine = None
        self.lines = []
        self.points = []  # To store drawn points
        self.actions = []  # To store actions for undo functionality
        self.pointSize = 6  # Increased size for better visibility
        self.closePointThreshold = 10  # Threshold to consider points as overlapping
        self.selectedItem = None
        self.axisLineX = None
        self.axisLineY = None
        self.mask = None
        self.colorToggled = False  # Track the current color state
        self.edited = False  # Track if the file has been edited
        
        self.imageFiles = []
        self.currentImageIndex = -1
        self.pixmapItem = None

        # Shortcuts
        self.shortcut_next = QShortcut(QKeySequence("D"), self)
        self.shortcut_next.activated.connect(self.next_image)
        self.shortcut_prev = QShortcut(QKeySequence("A"), self)
        self.shortcut_prev.activated.connect(self.prev_image)
        self.shortcut_escape = QShortcut(QKeySequence("Esc"), self)
        self.shortcut_escape.activated.connect(self.disable_drawing)
        self.shortcut_draw = QShortcut(QKeySequence("Ctrl+F"), self)
        self.shortcut_draw.activated.connect(self.fit_to_screen)
        self.shortcut_enable_drawing = QShortcut(QKeySequence("W"), self)
        self.shortcut_enable_drawing.activated.connect(self.enable_drawing)
        self.shortcut_undo = QShortcut(QKeySequence("Ctrl+Z"), self)
        self.shortcut_undo.activated.connect(self.undo)
        self.shortcut_delete = QShortcut(QKeySequence("Delete"), self)
        self.shortcut_delete.activated.connect(self.delete_selected_item)
        self.shortcut_save = QShortcut(QKeySequence("Ctrl+S"), self)
        self.shortcut_save.activated.connect(self.save_data)
        # Continous draw 
        self.continuous_drawing = False  # Track if we're in continuous line mode
        self.last_point = None  # Store the last point for continuous line drawing

        # Initialize Drawer after attributes are set
        self.drawer = Drawer(self)

        # Now safe to call Drawer methods
        self.drawer.update_scene()
        self.selected_class = None  # Track selected class
        self.classListWidget.currentItemChanged.connect(self.class_selected)  # Connect class selection
        # Add clear_scene_resources here
    def clear_scene_resources(self):
        self.scene.clear()  # Clears all items from the scene
        self.points.clear()
        self.lines.clear()
        self.actions.clear()
    # For continous draw
    def end_continuous_line(self):
        self.continuous_drawing = False
        self.last_point = None
        self.startPoint = None
        
    
    def add_mask(self):
        if self.pixmapItem:
            rect = self.pixmapItem.boundingRect()
            self.mask = self.scene.addRect(rect, QPen(Qt.NoPen), QColor(0, 0, 0, 100))

    def remove_mask(self):
        if self.mask:
            self.scene.removeItem(self.mask)
            self.mask = None

    def zoom_in(self):
        self.graphicsView.scale(1.2, 1.2)
        self.zooming = True

    def zoom_out(self):
        self.graphicsView.scale(0.8, 0.8)
        self.zooming = True

    def enable_drawing(self):
        self.drawing = True
        self.editing = False
        self.startPoint = None  # Reset startPoint for new drawing
        self.endPoint = None
        self.setCursor(QCursor(Qt.CrossCursor))
        self.update_axis_lines()
    
    def enable_editing(self):
        self.drawing = False
        self.editing = True
        self.setCursor(QCursor(Qt.OpenHandCursor))
        self.remove_axis_lines()

    def enable_editing_mode(self):
        """Enable editing mode for existing annotations"""
        self.editing = True
        self.drawing = False
        self.continuous_drawing = False
        self.last_point = None
        self.startPoint = None
        self.setCursor(QCursor(Qt.OpenHandCursor))

    
    def disable_drawing(self):
        self.drawing = False
        self.editing = False
        self.setCursor(QCursor(Qt.ArrowCursor))
        self.remove_axis_lines()
    
    def fit_to_screen(self):
        self.graphicsView.fitInView(self.scene.itemsBoundingRect(), Qt.KeepAspectRatio)
    
    def class_selected(self, current, previous):
        if current:
            self.selected_class = current.text()
        else:
            self.selected_class = None  # No class selected

    def add_new_class(self):
        new_class = self.classInput.text().strip()
        if new_class and not self.is_class_existing(new_class):
            self.classListWidget.addItem(new_class)
            self.classInput.clear()
        else:
            QMessageBox.warning(self, "Warning", "Class already exists or input is empty.")
    def is_class_existing(self, class_name):
        for index in range(self.classListWidget.count()):
            if self.classListWidget.item(index).text() == class_name:
                return True
        return False

    def save_data(self):
        if not self.imageFiles:
            return

        data = []
        img_width = self.pixmap.width()
        img_height = self.pixmap.height()
        
        for i, line_info in enumerate(self.lines):
            start = line_info["start"]
            end = line_info["end"]
            class_name = line_info.get("class", "None")

            data.append([i, start.x(), start.y(), end.x(), end.y(), img_width, img_height, class_name])

        folder = 'csv_data'
        if not os.path.exists(folder):
            os.makedirs(folder)
        filename = os.path.join(folder, os.path.splitext(os.path.basename(self.imageFiles[self.currentImageIndex]))[0] + ".csv")
        
        with open(filename, 'w') as f:
            writer = csv.writer(f)
            writer.writerow(["Index", "Start X", "Start Y", "End X", "End Y", "Image Width", "Image Height", "Class"])
            writer.writerows(data)

        self.edited = False

    # def update_data_table(self):
    #     self.dataTable.setRowCount(len(self.lines))
    #     for i, (start, end) in enumerate(self.lines):
    #         self.dataTable.setItem(i, 0, QTableWidgetItem(str(i)))
    #         self.dataTable.setItem(i, 1, QTableWidgetItem(f"{int(start.x())}"))
    #         self.dataTable.setItem(i, 2, QTableWidgetItem(f"{int(start.y())}"))
    #         self.dataTable.setItem(i, 3, QTableWidgetItem(f"{int(end.x())}"))
    #         self.dataTable.setItem(i, 4, QTableWidgetItem(f"{int(end.y())}"))
    def update_data_table(self):
        print(f"Lines data structure: {self.lines}")  # Debugging line to inspect data structure
        self.dataTable.setColumnCount(6)
        self.dataTable.setHorizontalHeaderLabels(["Index", "Start X", "Start Y", "End X", "End Y", "Class"])
        self.dataTable.setRowCount(len(self.lines))

        for i, line_info in enumerate(self.lines):
            # This will raise an error if line_info is a tuple
            start = line_info["start"]
            end = line_info["end"]
            class_name = line_info.get("class", "None")

            self.dataTable.setItem(i, 0, QTableWidgetItem(str(i)))
            self.dataTable.setItem(i, 1, QTableWidgetItem(f"{int(start.x())}"))
            self.dataTable.setItem(i, 2, QTableWidgetItem(f"{int(start.y())}"))
            self.dataTable.setItem(i, 3, QTableWidgetItem(f"{int(end.x())}"))
            self.dataTable.setItem(i, 4, QTableWidgetItem(f"{int(end.y())}"))
            self.dataTable.setItem(i, 5, QTableWidgetItem(class_name))


    

    def eventFilter(self, source, event):
        if source == self.graphicsView.viewport():
            if self.drawing:
                if event.type() == event.MouseButtonPress and event.button() == Qt.LeftButton:
                    if event.type() == event.MouseButtonDblClick:
                        self.zoom_in()  # Enable double-click zoom in drawing mode
                    else:
                        self.drawer.handle_mouse_press(event)  # Redirect to Drawer
                elif event.type() == event.MouseMove:
                    self.show_coordinates(event)
                    self.drawer.handle_mouse_move(event)  # Redirect to Drawer
                    self.update_axis_lines(event)  # Always show axis lines
                elif event.type() == event.MouseButtonDblClick and event.button() == Qt.LeftButton:
                    self.zoom_in()  # Enable double-click zoom in drawing mode

            elif self.editing:
                if event.type() == event.MouseButtonPress and event.button() == Qt.LeftButton:
                    if event.type() == event.MouseButtonDblClick:
                        self.zoom_in()  # Enable double-click zoom in editing mode
                    else:
                        self.handle_edit_press(event)
                elif event.type() == event.MouseMove and event.buttons() == Qt.LeftButton:
                    self.handle_edit_move(event)
                elif event.type() == event.MouseButtonRelease and event.button() == Qt.LeftButton:
                    self.handle_edit_release(event)
                elif event.type() == event.MouseMove:
                    self.handle_edit_hover(event)
                    self.update_axis_lines(event)  # Always show axis lines

            elif event.type() == event.MouseButtonDblClick and event.button() == Qt.LeftButton:
                self.zoom_in()
            elif event.type() == event.Wheel:
                self.handle_wheel_event(event)
            elif event.type() == event.MouseMove:
                self.update_axis_lines(event)
                self.show_coordinates(event)
            elif event.type() == event.MouseMove and event.buttons() == Qt.LeftButton and not self.drawing:
                self.graphicsView.setDragMode(QGraphicsView.ScrollHandDrag)
            elif event.type() == event.MouseButtonRelease:
                self.graphicsView.setDragMode(QGraphicsView.NoDrag)

        return super().eventFilter(source, event)

    def handle_mouse_move(self, event):
        scenePos = self.graphicsView.mapToScene(event.pos())
        nearby_point = self.get_nearby_point(scenePos)
        if isinstance(nearby_point, QPointF):
            self.setCursor(QCursor(Qt.CrossCursor))
        else:
            self.setCursor(QCursor(Qt.CrossCursor))
        if self.drawing:
            self.update_axis_lines(event)

    def handle_edit_press(self, event):
        scenePos = self.graphicsView.mapToScene(event.pos())
        scenePos = QPointF(int(scenePos.x()), int(scenePos.y()))
        item = self.scene.itemAt(scenePos, self.graphicsView.transform())
        
        if item and isinstance(item, QGraphicsEllipseItem):
            self.selectedItem = item
            self.setCursor(QCursor(Qt.ClosedHandCursor))
            item.setBrush(QColor(255, 0, 0, 100))  # Highlight selected item
        
        elif item and isinstance(item, QGraphicsLineItem):
            # Add a new point in the middle of the line
            line = item.line()
            midpoint = QPointF(
                int((line.p1().x() + line.p2().x()) / 2),
                int((line.p1().y() + line.p2().y()) / 2)
            )
            
            # Add new point
            new_item = self.scene.addEllipse(
                midpoint.x() - self.pointSize / 2,
                midpoint.y() - self.pointSize / 2,
                self.pointSize, self.pointSize,
                QPen(Qt.blue), QColor(Qt.blue)
            )
            
            point_info = {"point": midpoint, "item": new_item}
            self.points.append(point_info)
            self.actions.append({"type": "point", "point": point_info})
            
            # Update lines
            for i, (start, end) in enumerate(self.lines):
                if (abs(start.x() - line.p1().x()) < 1 and 
                    abs(start.y() - line.p1().y()) < 1 and 
                    abs(end.x() - line.p2().x()) < 1 and 
                    abs(end.y() - line.p2().y()) < 1):
                    # Remove old line and add two new lines
                    self.lines.pop(i)
                    self.lines.append((start, midpoint))
                    self.lines.append((midpoint, end))
                    break
            
            self.update_scene()
            self.update_data_table()
            self.edited = True

    def handle_edit_move(self, event):
        if self.selectedItem:
            scenePos = self.graphicsView.mapToScene(event.pos())
            scenePos = QPointF(int(scenePos.x()), int(scenePos.y()))
            old_center = self.selectedItem.rect().center()
            self.selectedItem.setRect(scenePos.x() - self.pointSize / 2, scenePos.y() - self.pointSize / 2, self.pointSize, self.pointSize)
            self.update_lines_with_moved_point(self.selectedItem, old_center, scenePos)
            self.edited = True

    def handle_edit_release(self, event):
        if self.selectedItem:
            self.selectedItem.setBrush(QColor(Qt.blue))  # Reset color after moving
            self.setCursor(QCursor(Qt.OpenHandCursor))
            self.selectedItem = None
            self.update_data_table()

    def handle_edit_hover(self, event):
        scenePos = self.graphicsView.mapToScene(event.pos())
        item = self.scene.itemAt(scenePos, self.graphicsView.transform())
        if item and isinstance(item, QGraphicsEllipseItem):
            self.setCursor(QCursor(Qt.SizeAllCursor))
        elif item and isinstance(item, QGraphicsLineItem):
            self.highlight_from_scene(item)
        else:
            self.setCursor(QCursor(Qt.OpenHandCursor))

    def handle_wheel_event(self, event: QWheelEvent):
        if event.angleDelta().y() > 0:
            self.zoom_in()
        else:
            self.zoom_out()

    def break_line_if_needed(self, start, end):
        for i, (line_start, line_end) in enumerate(self.lines):
            if self.point_on_line(end, line_start, line_end):
                self.lines.pop(i)
                self.lines.append((line_start, end))
                self.lines.append((end, line_end))
                break

    def point_on_line(self, point, line_start, line_end):
        dxc = point.x() - line_start.x()
        dyc = point.y() - line_start.y()
        dxl = line_end.x() - line_start.x()
        dyl = line_end.y() - line_start.y()
        cross = dxc * dyl - dyc * dxl
        if abs(cross) > self.closePointThreshold:
            return False
        if abs(dxl) >= abs(dyl):
            if dxl > 0:
                return line_start.x() <= point.x() <= line_end.x()
            else:
                return line_end.x() <= point.x() <= line_start.x()
        else:
            if dyl > 0:
                return line_start.y() <= point.y() <= line_end.y()
            else:
                return line_end.y() <= point.y() <= line_start.y()

    def get_nearby_point(self, point):
        for pt in self.points:
            if (point - pt["point"]).manhattanLength() < self.closePointThreshold:
                return pt["point"]
        return QPointF(int(point.x()), int(point.y()))

    def close_to_point(self, p1, p2):
        return (p1 - p2).manhattanLength() < self.closePointThreshold

    def update_axis_lines(self, event=None):
        try:
            # Always remove existing axis lines first
            if self.axisLineX and self.axisLineX.scene() == self.scene:
                self.scene.removeItem(self.axisLineX)
            if self.axisLineY and self.axisLineY.scene() == self.scene:
                self.scene.removeItem(self.axisLineY)
                
            # Reset references
            self.axisLineX = None
            self.axisLineY = None
            
            # Get current scene position
            if event:
                scenePos = self.graphicsView.mapToScene(event.pos())
                
                # Get scene dimensions
                sceneRect = self.scene.sceneRect()
                
                # Create new axis lines that span the entire scene
                self.axisLineX = self.scene.addLine(
                    sceneRect.left(), scenePos.y(),
                    sceneRect.right(), scenePos.y(),
                    QPen(QColor(200, 200, 200), 1, Qt.DashLine)
                )
                self.axisLineY = self.scene.addLine(
                    scenePos.x(), sceneRect.top(),
                    scenePos.x(), sceneRect.bottom(),
                    QPen(QColor(200, 200, 200), 1, Qt.DashLine)
                )
                
                # Ensure axis lines stay on top
                self.axisLineX.setZValue(9999)
                self.axisLineY.setZValue(9999)
                
        except RuntimeError as e:
            print(f"Warning: {e}")
            self.axisLineX = None
            self.axisLineY = None

    def show_coordinates(self, event):
        scenePos = self.graphicsView.mapToScene(event.pos())
        #self.coordinatesLabel.setText(f"X: {scenePos.x():.2f}, Y: {scenePos.y():.2f}")
        self.coordinatesLabel.setText(f"X: {int(scenePos.x())}, Y: {int(scenePos.y())}")

    def remove_axis_lines(self):
        try:
            if self.axisLineX and self.axisLineX.scene() == self.scene:
                self.scene.removeItem(self.axisLineX)
            if self.axisLineY and self.axisLineY.scene() == self.scene:
                self.scene.removeItem(self.axisLineY)
            self.axisLineX = None
            self.axisLineY = None
        except RuntimeError as e:
            print(f"Warning: {e}")

    def highlight_from_table(self, row, column):
        # Highlight the row in the table
        self.dataTable.selectRow(row)
        # Highlight the corresponding points and lines in the scene
        start_item = self.dataTable.item(row, 1)
        start_x = float(start_item.text()) if start_item else None
        start_y = float(self.dataTable.item(row, 2).text()) if start_item else None
        end_x = float(self.dataTable.item(row, 3).text()) if start_item else None
        end_y = float(self.dataTable.item(row, 4).text()) if start_item else None
        for p in self.points:
            if (p["point"].x() == start_x and p["point"].y() == start_y) or (p["point"].x() == end_x and p["point"].y() == end_y):
                p["item"].setBrush(QColor(255, 0, 0, 100))  # Highlight
            else:
                p["item"].setBrush(QColor(Qt.blue))  # Reset color
        for item in self.scene.items():
            if isinstance(item, QGraphicsLineItem):
                data = item.data(0)
                if data and ((data["start"].x() == start_x and data["start"].y() == start_y and data["end"].x() == end_x and data["end"].y() == end_y) or
                             (data["start"].x() == end_x and data["start"].y() == end_y and data["end"].x() == start_x and data["end"].y() == start_y)):
                    item.setPen(QPen(QColor(255, 0, 0), 2))  # Highlight
                else:
                    item.setPen(QPen(QColor(0, 255, 0), 2))  # Reset color

    def highlight_from_scene(self, item):
        if isinstance(item, QGraphicsEllipseItem):
            for i, p in enumerate(self.points):
                if p["item"] == item:
                    point = p["point"]
                    for row in range(self.dataTable.rowCount()):
                        start_item = self.dataTable.item(row, 1)
                        start_x = float(start_item.text()) if start_item else None
                        start_y = float(self.dataTable.item(row, 2).text()) if start_item else None
                        end_x = float(self.dataTable.item(row, 3).text()) if start_item else None
                        end_y = float(self.dataTable.item(row, 4).text()) if start_item else None
                        if (point.x() == start_x and point.y() == start_y) or (point.x() == end_x and point.y() == end_y):
                            self.dataTable.selectRow(row)
                            item.setBrush(QColor(255, 0, 0, 100))  # Highlight
                        else:
                            p["item"].setBrush(QColor(Qt.blue))  # Reset color
        elif isinstance(item, QGraphicsLineItem):
            data = item.data(0)
            if data:
                start = data["start"]
                end = data["end"]
                for row in range(self.dataTable.rowCount()):
                    start_item = self.dataTable.item(row, 1)
                    start_x = float(start_item.text()) if start_item else None
                    start_y = float(self.dataTable.item(row, 2).text()) if start_item else None
                    end_x = float(self.dataTable.item(row, 3).text()) if start_item else None
                    end_y = float(self.dataTable.item(row, 4).text()) if start_item else None
                    if (start.x() == start_x and start.y() == start_y and end.x() == end_x and end.y() == end_y) or (start.x() == end_x and start.y() == end_y and end.x() == start_x and end.y() == start_y):
                        self.dataTable.selectRow(row)
                        item.setPen(QPen(QColor(255, 0, 0), 2))  # Highlight
                        for p in self.points:
                            if (p["point"].x() == start.x() and p["point"].y() == start.y()) or (p["point"].x() == end.x() and p["point"].y() == end.y()):
                                p["item"].setBrush(QColor(255, 0, 0, 100))  # Highlight
                            else:
                                p["item"].setBrush(QColor(Qt.blue))  # Reset color


    def show_context_menu(self, pos):
        contextMenu = QMenu(self)
        deleteAction = contextMenu.addAction("Delete")
        action = contextMenu.exec_(self.dataTable.mapToGlobal(pos))
        if action == deleteAction:
            self.delete_selected_item()
    
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Delete:
            current_row = self.dataTable.currentRow()
            if current_row >= 0:
                self.delete_row(current_row)
        elif event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            if self.drawing and self.continuous_drawing:
                self.end_continuous_line()

    def ask_save_changes(self):
        reply = QMessageBox.question(self, 'Save Changes', 'Do you want to save changes?', QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
        return reply

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AnnotationTool()
    window.show()
    sys.exit(app.exec_())
