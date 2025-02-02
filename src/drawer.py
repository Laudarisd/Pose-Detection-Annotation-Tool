import sys
import os
import csv
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QLabel, QWidget, QPushButton, QFileDialog, QTableWidget, QTableWidgetItem, QGraphicsView, QGraphicsScene, QShortcut, QListWidget, QGraphicsPixmapItem, QGraphicsEllipseItem, QHeaderView, QGraphicsLineItem, QMessageBox, QSplitter, QMenu
from PyQt5.QtCore import Qt, QPointF, QRectF, QEvent
from PyQt5.QtGui import QPixmap, QPen, QColor, QKeySequence, QCursor, QPainter, QWheelEvent


class Drawer:
    def __init__(self, main_window):
        self.main = main_window  # Store reference to main window

    def handle_mouse_press(self, event):
        scenePos = self.main.graphicsView.mapToScene(event.pos())
        # Convert coordinates to integers for better precision
        scenePos = QPointF(int(scenePos.x()), int(scenePos.y()))

        item = self.main.scene.itemAt(scenePos, self.main.graphicsView.transform())
        # Check for double-click during continuous drawing
        if self.main.drawing and self.main.continuous_drawing and event.type() == QEvent.MouseButtonDblClick:
            self.end_continuous_line()
            return

        if self.main.drawing:
            nearby_point = self.get_nearby_point(scenePos)
            selected_class = self.main.selected_class if self.main.selected_class else "None"

            if not self.main.continuous_drawing:
                # Start new continuous line sequence
                self.main.continuous_drawing = True
                self.main.startPoint = {
                    "point": nearby_point,
                    "item": self.main.scene.addEllipse(
                        nearby_point.x() - self.main.pointSize / 2,
                        nearby_point.y() - self.main.pointSize / 2,
                        self.main.pointSize, self.main.pointSize,
                        QPen(Qt.blue), QColor(Qt.blue)
                    ),
                    "class": selected_class
                }
                point_info = {"point": self.main.startPoint["point"], "item": self.main.startPoint["item"], "class": selected_class}
                self.main.points.append(point_info)
                self.main.actions.append({"type": "point", "point": point_info})
                self.main.last_point = self.main.startPoint
            else:
                # Continue the line sequence
                self.main.endPoint = {
                    "point": nearby_point,
                    "item": self.main.scene.addEllipse(
                        nearby_point.x() - self.main.pointSize / 2,
                        nearby_point.y() - self.main.pointSize / 2,
                        self.main.pointSize, self.main.pointSize,
                        QPen(Qt.blue), QColor(Qt.blue)
                    ),
                    "class": selected_class
                }
                point_info = {"point": self.main.endPoint["point"], "item": self.main.endPoint["item"], "class": selected_class}
                self.main.points.append(point_info)
                self.main.actions.append({"type": "point", "point": point_info})

                # Add line from last point to current point with class information
                self.main.lines.append({
                    "start": self.main.last_point["point"],
                    "end": self.main.endPoint["point"],
                    "class": selected_class
                })
                self.main.actions.append({"type": "line", "class": selected_class})

                self.update_scene()
                self.main.update_data_table()
                self.main.last_point = self.main.endPoint
                self.main.edited = True

        elif self.main.editing and isinstance(item, QGraphicsEllipseItem):
            self.main.selectedItem = item
            self.main.setCursor(QCursor(Qt.ClosedHandCursor))
            item.setBrush(QColor(255, 0, 0, 100))  # Highlight selected item

        elif self.main.editing and isinstance(item, QGraphicsLineItem):
            line = item.line()
            new_point = QPointF(int((line.p1().x() + line.p2().x()) / 2), int((line.p1().y() + line.p2().y()) / 2))
            new_item = self.main.scene.addEllipse(
                new_point.x() - self.main.pointSize / 2,
                new_point.y() - self.main.pointSize / 2,
                self.main.pointSize, self.main.pointSize,
                QPen(Qt.blue), QColor(Qt.blue)
            )
            point_info = {"point": new_point, "item": new_item, "class": selected_class}
            self.main.points.append(point_info)
            self.main.actions.append({"type": "point", "point": point_info})
            self.update_scene()
            self.main.update_data_table()
            self.main.edited = True

        elif item:
            self.main.highlight_from_scene(item)



    def get_nearby_point(self, point):
        for pt in self.main.points:
            if (point - pt["point"]).manhattanLength() < self.main.closePointThreshold:
                return pt["point"]
        return QPointF(int(point.x()), int(point.y()))

    

    def update_scene(self):
        try:
            # Clear only the lines and circles, excluding the pixmap and mask
            items_to_remove = []
            for item in self.main.scene.items():
                if (item != self.main.pixmapItem and 
                    item != self.main.mask and 
                    not isinstance(item, QGraphicsEllipseItem)):
                    items_to_remove.append(item)

            # Safely remove items
            for item in items_to_remove:
                if item.scene() == self.main.scene:
                    self.main.scene.removeItem(item)

            # Add new lines and points
            pen = QPen(QColor(0, 255, 0), 2)
            for line in self.main.lines:
                start = line["start"]
                end = line["end"]
                class_name = line.get("class", "None")  # Retrieve class if exists

                line_item = self.main.scene.addLine(start.x(), start.y(), end.x(), end.y(), pen)
                line_item.setData(0, {"start": start, "end": end, "class": class_name})

                color = Qt.blue
                if (start - end).manhattanLength() < self.main.closePointThreshold:
                    color = Qt.magenta

                self.main.scene.addEllipse(
                    start.x() - self.main.pointSize / 2, 
                    start.y() - self.main.pointSize / 2,
                    self.main.pointSize, self.main.pointSize, 
                    QPen(color), QColor(color)
                )
                self.main.scene.addEllipse(
                    end.x() - self.main.pointSize / 2,
                    end.y() - self.main.pointSize / 2,
                    self.main.pointSize, self.main.pointSize,
                    QPen(color), QColor(color)
                )

            # Add start point if it exists
            if self.main.startPoint:
                self.main.scene.addEllipse(
                    self.main.startPoint["point"].x() - self.main.pointSize / 2,
                    self.main.startPoint["point"].y() - self.main.pointSize / 2,
                    self.main.pointSize, self.main.pointSize,
                    QPen(Qt.blue), QColor(Qt.blue)
                )

            self.main.update_axis_lines()

        except RuntimeError as e:
            print(f"Warning: {e}")

    def update_lines_with_moved_point(self, selectedItem, oldPos, newPos):
        center = oldPos
        for i, (start, end) in enumerate(self.main.lines):
            if (center - start).manhattanLength() < self.main.closePointThreshold:
                self.main.lines[i] = (newPos, end)
                self.remove_point(start)
                self.main.points.append({"point": newPos, "item": selectedItem})
            elif (center - end).manhattanLength() < self.main.closePointThreshold:
                self.main.lines[i] = (start, newPos)
                self.remove_point(end)
                self.main.points.append({"point": newPos, "item": selectedItem})
        self.update_scene()
        self.main.update_data_table()

    def handle_mouse_move(self, event):
        scenePos = self.main.graphicsView.mapToScene(event.pos())  # Access graphicsView through self.main
        nearby_point = self.get_nearby_point(scenePos)
        
        if isinstance(nearby_point, QPointF):
            self.main.setCursor(QCursor(Qt.CrossCursor))  # Use self.main.setCursor
        else:
            self.main.setCursor(QCursor(Qt.CrossCursor))

        if self.main.drawing:
            self.main.update_axis_lines(event)  # Use self.main.update_axis_lines

    def remove_point(self, point):
        """
        Remove a point from the scene and points list.
        This method is for internal use by the Drawer class.
        """
        points_to_remove = []
        # Use self.main.points if called from Drawer instance
        # or self.points if called from AnnotationTool instance
        points_list = self.main.points if hasattr(self, 'main') else self.points
        scene = self.main.scene if hasattr(self, 'main') else self.scene
        
        for p in points_list:
            if p["point"] == point:
                try:
                    if p["item"].scene() == scene:
                        scene.removeItem(p["item"])
                    points_to_remove.append(p)
                except:
                    points_to_remove.append(p)
        
        for p in points_to_remove:
            if p in points_list:
                points_list.remove(p)


    def end_continuous_line(self):
        self.main.continuous_drawing = False
        self.main.last_point = None
        self.main.startPoint = None