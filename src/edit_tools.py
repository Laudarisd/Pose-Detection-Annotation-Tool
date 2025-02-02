import sys
import os
import csv
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QLabel, QWidget, QPushButton, QFileDialog, QTableWidget, QTableWidgetItem, QGraphicsView, QGraphicsScene, QShortcut, QListWidget, QGraphicsPixmapItem, QGraphicsEllipseItem, QHeaderView, QGraphicsLineItem, QMessageBox, QSplitter, QMenu
from PyQt5.QtCore import Qt, QPointF, QRectF, QEvent
from PyQt5.QtGui import QPixmap, QPen, QColor, QKeySequence, QCursor, QPainter, QWheelEvent


class EditTools:

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

    def undo(self):
        if self.actions:
            last_action = self.actions.pop()
            
            if last_action["type"] == "line":
                line = self.lines.pop()
                last_point = line["end"]
                
                points_to_remove = []
                for p in self.points:
                    if p["point"] == last_point:
                        try:
                            if p["item"].scene() == self.scene:
                                self.scene.removeItem(p["item"])
                            points_to_remove.append(p)
                        except:
                            points_to_remove.append(p)
                
                for p in points_to_remove:
                    if p in self.points:
                        self.points.remove(p)
                
                if self.continuous_drawing:
                    for p in self.points:
                        if p["point"] == line["start"]:
                            self.last_point = p
                            break
            
            elif last_action["type"] == "point":
                point_to_remove = last_action["point"]
                self.remove_point(point_to_remove["point"])
            
            # Corrected to call update_scene from Drawer
            self.drawer.update_scene()
            self.update_data_table()
            self.edited = True





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

    def delete_row(self, row):
        """Delete a row and its corresponding points and lines"""
        if row < 0 or row >= len(self.lines):
            return

        # Get points from the line we're deleting
        start = self.lines[row]['start']
        end = self.lines[row]['end']

        # Remove the line
        self.lines.pop(row)

        # Find and remove points that are no longer connected to any lines
        points_to_check = [start, end]
        for point in points_to_check:
            # Check if point is used in any remaining lines
            point_in_use = False
            for line in self.lines:
                line_start = line['start']
                line_end = line['end']
                if (self.close_to_point(point, line_start) or 
                    self.close_to_point(point, line_end)):
                    point_in_use = True
                    break

            # If point is not used, remove it
            if not point_in_use:
                # Find and remove the point from self.points
                for p in self.points[:]:  # Create a copy of the list to iterate
                    if self.close_to_point(point, p["point"]):
                        if p["item"].scene() == self.scene:
                            self.scene.removeItem(p["item"])
                        self.points.remove(p)

        # Update the scene and table
        self.drawer.update_scene()
        self.update_data_table()
        self.edited = True
