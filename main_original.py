import sys
import os
import csv
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QLabel, QWidget, QPushButton, QFileDialog, QTableWidget, QTableWidgetItem, QGraphicsView, QGraphicsScene, QShortcut, QListWidget, QGraphicsPixmapItem, QGraphicsEllipseItem, QHeaderView, QGraphicsLineItem, QMessageBox, QSplitter, QMenu
from PyQt5.QtCore import Qt, QPointF, QRectF, QEvent
from PyQt5.QtGui import QPixmap, QPen, QColor, QKeySequence, QCursor, QPainter, QWheelEvent

class AnnotationTool(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Pose Detection Annotation Tool")
        self.setGeometry(100, 100, 1200, 800)
        
        # Central widget
        self.centralWidget = QWidget(self)
        self.setCentralWidget(self.centralWidget)

        # Layouts
        self.mainLayout = QHBoxLayout(self.centralWidget)
        
        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setChildrenCollapsible(False)
        
        self.leftWidget = QWidget()
        self.leftPanel = QVBoxLayout(self.leftWidget)
        
        self.midWidget = QWidget()
        self.midPanel = QVBoxLayout(self.midWidget)
        
        self.rightWidget = QWidget()
        self.rightPanel = QVBoxLayout(self.rightWidget)
        
        self.splitter.addWidget(self.leftWidget)
        self.splitter.addWidget(self.midWidget)
        self.splitter.addWidget(self.rightWidget)
        
        self.splitter.setSizes([180, 840, 180])  # Set initial sizes to maintain original proportions
        
        self.mainLayout.addWidget(self.splitter)
        
        # Left panel
        self.uploadButton = QPushButton("Upload Folder", self)
        self.uploadButton.clicked.connect(self.upload_folder)
        self.leftPanel.addWidget(self.uploadButton)

        self.fileListWidget = QListWidget(self)
        self.fileListWidget.itemSelectionChanged.connect(self.load_image)
        self.leftPanel.addWidget(self.fileListWidget)

        self.zoomInButton = QPushButton("Zoom In", self)
        self.zoomInButton.clicked.connect(self.zoom_in)
        self.leftPanel.addWidget(self.zoomInButton)
        
        self.zoomOutButton = QPushButton("Zoom Out", self)
        self.zoomOutButton.clicked.connect(self.zoom_out)
        self.leftPanel.addWidget(self.zoomOutButton)

        self.drawLineButton = QPushButton("Draw Line", self)
        self.drawLineButton.clicked.connect(self.enable_drawing)
        self.leftPanel.addWidget(self.drawLineButton)

        self.editButton = QPushButton("Edit", self)
        self.editButton.clicked.connect(self.enable_editing)
        self.leftPanel.addWidget(self.editButton)

        self.changeColorButton = QPushButton("Change Color", self)
        self.changeColorButton.clicked.connect(self.change_color_mode)
        self.leftPanel.addWidget(self.changeColorButton)

        # Mid panel
        self.graphicsView = QGraphicsView(self)
        self.graphicsView.setRenderHint(QPainter.Antialiasing)
        self.scene = QGraphicsScene(self)
        self.graphicsView.setScene(self.scene)
        self.graphicsView.viewport().installEventFilter(self)
        self.midPanel.addWidget(self.graphicsView)

        self.coordinatesLabel = QLabel(self)
        self.coordinatesLabel.setAlignment(Qt.AlignRight | Qt.AlignTop)
        self.midPanel.addWidget(self.coordinatesLabel)

        # Right panel
        self.dataTable = QTableWidget(self)
        self.dataTable.setColumnCount(5)
        self.dataTable.setHorizontalHeaderLabels(["Index", "Start X", "Start Y", "End X", "End Y"])
        self.rightPanel.addWidget(self.dataTable)
        
        self.dataTable.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)  # Allow resizing columns
        self.dataTable.cellClicked.connect(self.highlight_from_table)  # Connect cell click to highlight function
        self.dataTable.setContextMenuPolicy(Qt.CustomContextMenu)  # Enable custom context menu
        self.dataTable.customContextMenuRequested.connect(self.show_context_menu)  # Connect context menu request to handler

        self.saveButton = QPushButton("Save Data", self)
        self.saveButton.clicked.connect(self.save_data)
        self.rightPanel.addWidget(self.saveButton)
        
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
                self.update_scene()  # Update scene to show loaded annotations
            
            self.update_data_table()
            self.edited = False  # Reset edited flag when loading a new image

    def load_data(self):
        csv_file = os.path.join('csv_data', os.path.splitext(os.path.basename(self.imageFiles[self.currentImageIndex]))[0] + ".csv")
        if os.path.exists(csv_file):
            try:
                with open(csv_file, 'r') as f:
                    reader = csv.DictReader(f)
                    if not {"Start X", "Start Y", "End X", "End Y"}.issubset(reader.fieldnames):
                        print("CSV file is missing required columns.")
                        return False
                    
                    # Clear existing data
                    self.lines.clear()
                    self.points.clear()
                    
                    # Load points and lines from CSV
                    for row in reader:
                        start_point = QPointF(int(float(row["Start X"])), int(float(row["Start Y"])))
                        end_point = QPointF(int(float(row["End X"])), int(float(row["End Y"])))
                        
                        # Add start point
                        start_item = self.scene.addEllipse(
                            start_point.x() - self.pointSize / 2,
                            start_point.y() - self.pointSize / 2,
                            self.pointSize, self.pointSize,
                            QPen(Qt.blue), QColor(Qt.blue)
                        )
                        self.points.append({"point": start_point, "item": start_item})
                        
                        # Add end point
                        end_item = self.scene.addEllipse(
                            end_point.x() - self.pointSize / 2,
                            end_point.y() - self.pointSize / 2,
                            self.pointSize, self.pointSize,
                            QPen(Qt.blue), QColor(Qt.blue)
                        )
                        self.points.append({"point": end_point, "item": end_item})
                        
                        # Add line
                        self.lines.append((start_point, end_point))
                    
                    return True
            except Exception as e:
                print(f"Error loading annotation file: {e}")
                return False
        return False
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
    
    def next_image(self):
        if self.edited:
            result = self.ask_save_changes()
            if result == QMessageBox.Yes:
                self.save_data()
            elif result == QMessageBox.Cancel:
                return
        if self.currentImageIndex < len(self.imageFiles) - 1:
            self.currentImageIndex += 1
            self.fileListWidget.setCurrentRow(self.currentImageIndex)
            self.load_image()
    
    def prev_image(self):
        if self.edited:
            result = self.ask_save_changes()
            if result == QMessageBox.Yes:
                self.save_data()
            elif result == QMessageBox.Cancel:
                return
        if self.currentImageIndex > 0:
            self.currentImageIndex -= 1
            self.fileListWidget.setCurrentRow(self.currentImageIndex)
            self.load_image()
    
    def save_data(self):
        if not self.imageFiles:
            return

        data = []
        img_width = self.pixmap.width()
        img_height = self.pixmap.height()
        for i, (start, end) in enumerate(self.lines):
            data.append([i, start.x(), start.y(), end.x(), end.y(), img_width, img_height])
        
        folder = 'csv_data'
        if not os.path.exists(folder):
            os.makedirs(folder)
        filename = os.path.join(folder, os.path.splitext(os.path.basename(self.imageFiles[self.currentImageIndex]))[0] + ".csv")
        
        with open(filename, 'w') as f:
            writer = csv.writer(f)
            writer.writerow(["Index", "Start X", "Start Y", "End X", "End Y", "Image Width", "Image Height"])
            writer.writerows(data)
        self.edited = False  # Reset edited flag after saving

    def update_data_table(self):
        self.dataTable.setRowCount(len(self.lines))
        for i, (start, end) in enumerate(self.lines):
            self.dataTable.setItem(i, 0, QTableWidgetItem(str(i)))
            self.dataTable.setItem(i, 1, QTableWidgetItem(f"{int(start.x())}"))
            self.dataTable.setItem(i, 2, QTableWidgetItem(f"{int(start.y())}"))
            self.dataTable.setItem(i, 3, QTableWidgetItem(f"{int(end.x())}"))
            self.dataTable.setItem(i, 4, QTableWidgetItem(f"{int(end.y())}"))
    def undo(self):
        if self.actions:
            last_action = self.actions.pop()
            if last_action["type"] == "line":
                # Remove the last line
                line = self.lines.pop()
                # Remove only the last point (end point of the line)
                last_point = line[1]  # Get the end point
                
                # Safely remove point and its item
                points_to_remove = []
                for p in self.points:
                    if p["point"] == last_point:
                        try:
                            if p["item"].scene() == self.scene:  # Check if item belongs to current scene
                                self.scene.removeItem(p["item"])
                            points_to_remove.append(p)
                        except:
                            # If there's any error removing the item, just note the point for removal
                            points_to_remove.append(p)
                
                # Remove points from our points list
                for p in points_to_remove:
                    if p in self.points:
                        self.points.remove(p)
                
                # Update the last_point to the previous point in the sequence
                if self.continuous_drawing:
                    for p in self.points:
                        if p["point"] == line[0]:
                            self.last_point = p
                            break
            
            elif last_action["type"] == "point":
                point_to_remove = last_action["point"]
                self.remove_point(point_to_remove["point"])
            
            self.update_scene()
            self.update_data_table()
            self.edited = True
    def remove_point(self, point):
        points_to_remove = []
        for p in self.points:
            if p["point"] == point:
                try:
                    if p["item"].scene() == self.scene:  # Check if item belongs to current scene
                        self.scene.removeItem(p["item"])
                    points_to_remove.append(p)
                except:
                    points_to_remove.append(p)
        
        # Remove points from our points list
        for p in points_to_remove:
            if p in self.points:
                self.points.remove(p)

    def delete_selected_item(self):
        current_row = self.dataTable.currentRow()
        if current_row >= 0:
            self.delete_row(current_row)

    def remove_lines_with_point(self, point):
        self.lines = [line for line in self.lines if not (self.close_to_point(point, line[0]) or self.close_to_point(point, line[1]))]

    def change_color_mode(self):
        if self.colorToggled:
            self.setStyleSheet("")
            self.dataTable.setStyleSheet("")
            self.graphicsView.setStyleSheet("")
            self.remove_mask()
        else:
            self.setStyleSheet("background-color: lightgray; color: black;")
            self.dataTable.setStyleSheet("background-color: lightgray; color: black;")
            self.graphicsView.setStyleSheet("background-color: lightgray; color: black;")
            self.add_mask()
        self.colorToggled = not self.colorToggled

    def eventFilter(self, source, event):
        if source == self.graphicsView.viewport():
            if self.drawing:
                if event.type() == event.MouseButtonPress and event.button() == Qt.LeftButton:
                    if event.type() == event.MouseButtonDblClick:
                        self.zoom_in()  # Enable double-click zoom in drawing mode
                    else:
                        self.handle_mouse_press(event)
                elif event.type() == event.MouseMove:
                    self.show_coordinates(event)
                    self.handle_mouse_move(event)
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
    
    def handle_mouse_press(self, event):
        scenePos = self.graphicsView.mapToScene(event.pos())
        # Convert coordinates to integers
        scenePos = QPointF(int(scenePos.x()), int(scenePos.y()))
        
        item = self.scene.itemAt(scenePos, self.graphicsView.transform())
        # Check for double-click during continuous drawing
        if self.drawing and self.continuous_drawing and event.type() == QEvent.MouseButtonDblClick:
            self.end_continuous_line()
            return
        
        if self.drawing:
            nearby_point = self.get_nearby_point(scenePos)
            if not self.continuous_drawing:
                # Start new continuous line sequence
                self.continuous_drawing = True
                self.startPoint = {"point": nearby_point, "item": self.scene.addEllipse(nearby_point.x() - self.pointSize / 2, nearby_point.y() - self.pointSize / 2, self.pointSize, self.pointSize, QPen(Qt.blue), QColor(Qt.blue))}
                point_info = {"point": self.startPoint["point"], "item": self.startPoint["item"]}
                self.points.append(point_info)
                self.actions.append({"type": "point", "point": point_info})  # Store the action for undo
                self.last_point = self.startPoint
            else:
                # Continue the line sequence
                self.endPoint = {"point": nearby_point, "item": self.scene.addEllipse(nearby_point.x() - self.pointSize / 2, nearby_point.y() - self.pointSize / 2, self.pointSize, self.pointSize, QPen(Qt.blue), QColor(Qt.blue))}
                point_info = {"point": self.endPoint["point"], "item": self.endPoint["item"]}
                self.points.append(point_info)
                self.actions.append({"type": "point", "point": point_info})  # Store the action for undo
                
                # Add line from last point to current point
                self.lines.append((self.last_point["point"], self.endPoint["point"]))
                self.actions.append({"type": "line"})  # Store the action for undo
                self.update_scene()
                self.update_data_table()
                self.last_point = self.endPoint
                self.edited = True
                
        elif self.editing and isinstance(item, QGraphicsEllipseItem):
            self.selectedItem = item
            self.setCursor(QCursor(Qt.ClosedHandCursor))
            item.setBrush(QColor(255, 0, 0, 100))  # Highlight selected item
            
        elif self.editing and isinstance(item, QGraphicsLineItem):
            line = item.line()
            new_point = QPointF(int((line.p1().x() + line.p2().x()) / 2), int((line.p1().y() + line.p2().y()) / 2))
            new_item = self.scene.addEllipse(new_point.x() - self.pointSize / 2, new_point.y() - self.pointSize / 2, self.pointSize, self.pointSize, QPen(Qt.blue), QColor(Qt.blue))
            point_info = {"point": new_point, "item": new_item}
            self.points.append(point_info)
            self.actions.append({"type": "point", "point": point_info})  # Store the action for undo
            self.update_scene()
            self.update_data_table()
            self.edited = True
            
        elif item:
            self.highlight_from_scene(item)

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

    def update_lines_with_moved_point(self, selectedItem, oldPos, newPos):
        center = oldPos
        for i, (start, end) in enumerate(self.lines):
            if (center - start).manhattanLength() < self.closePointThreshold:
                self.lines[i] = (newPos, end)
                self.remove_point(start)
                self.points.append({"point": newPos, "item": selectedItem})
            elif (center - end).manhattanLength() < self.closePointThreshold:
                self.lines[i] = (start, newPos)
                self.remove_point(end)
                self.points.append({"point": newPos, "item": selectedItem})
        self.update_scene()
        self.update_data_table()

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

    def update_scene(self):
        try:
            # Clear only the lines and circles, excluding the pixmap and mask
            items_to_remove = []
            for item in self.scene.items():
                if (item != self.pixmapItem and 
                    item != self.mask and 
                    not isinstance(item, QGraphicsEllipseItem)):
                    items_to_remove.append(item)

            # Safely remove items
            for item in items_to_remove:
                if item.scene() == self.scene:
                    self.scene.removeItem(item)

            # Add new lines and points
            pen = QPen(QColor(0, 255, 0), 2)
            for start, end in self.lines:
                line_item = self.scene.addLine(start.x(), start.y(), end.x(), end.y(), pen)
                line_item.setData(0, {"start": start, "end": end})
                
                color = Qt.blue
                if (start - end).manhattanLength() < self.closePointThreshold:
                    color = Qt.magenta

                self.scene.addEllipse(start.x() - self.pointSize / 2, 
                                    start.y() - self.pointSize / 2,
                                    self.pointSize, self.pointSize, 
                                    QPen(color), QColor(color))
                self.scene.addEllipse(end.x() - self.pointSize / 2,
                                    end.y() - self.pointSize / 2,
                                    self.pointSize, self.pointSize,
                                    QPen(color), QColor(color))

            # Add start point if it exists
            if self.startPoint:
                self.scene.addEllipse(self.startPoint["point"].x() - self.pointSize / 2,
                                    self.startPoint["point"].y() - self.pointSize / 2,
                                    self.pointSize, self.pointSize,
                                    QPen(Qt.blue), QColor(Qt.blue))

            self.update_axis_lines()
        except RuntimeError as e:
            print(f"Warning: {e}")

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

    def delete_row(self, row):
        if row < 0 or row >= self.dataTable.rowCount():
            return
        start_item = self.dataTable.item(row, 1)
        start_x = float(start_item.text()) if start_item else None
        start_y = float(self.dataTable.item(row, 2).text()) if start_item else None
        end_x = float(self.dataTable.item(row, 3).text()) if start_item else None
        end_y = float(self.dataTable.item(row, 4).text()) if start_item else None
        points_to_remove = [QPointF(start_x, start_y), QPointF(end_x, end_y)]
        self.lines.pop(row)
        for p in points_to_remove:
            self.remove_point(p)
        self.update_scene()
        self.update_data_table()
        self.edited = True

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
