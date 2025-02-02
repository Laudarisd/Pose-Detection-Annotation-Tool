import sys
import os
import csv
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QLabel, QWidget, QPushButton, QFileDialog, QTableWidget, QTableWidgetItem, QGraphicsView, QGraphicsScene, QShortcut, QListWidget, QGraphicsPixmapItem, QGraphicsEllipseItem, QHeaderView, QGraphicsLineItem, QMessageBox, QSplitter, QMenu, QLineEdit
from PyQt5.QtCore import Qt, QPointF, QRectF, QEvent
from PyQt5.QtGui import QPixmap, QPen, QColor, QKeySequence, QCursor, QPainter, QWheelEvent


class UISetup:

    def setup_ui(self):
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
        
    def setup_left_panel(self):
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

    def setup_mid_panel(self):
        self.graphicsView = QGraphicsView(self)
        self.graphicsView.setRenderHint(QPainter.Antialiasing)
        self.scene = QGraphicsScene(self)
        self.graphicsView.setScene(self.scene)
        self.graphicsView.viewport().installEventFilter(self)
        self.midPanel.addWidget(self.graphicsView)

        self.coordinatesLabel = QLabel(self)
        self.coordinatesLabel.setAlignment(Qt.AlignRight | Qt.AlignTop)
        self.midPanel.addWidget(self.coordinatesLabel)

    # def setup_right_panel(self):
    #     self.dataTable = QTableWidget(self)
    #     self.dataTable.setColumnCount(5)
    #     self.dataTable.setHorizontalHeaderLabels(["Index", "Start X", "Start Y", "End X", "End Y"])
    #     self.rightPanel.addWidget(self.dataTable)
        
    #     self.dataTable.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)  # Allow resizing columns
    #     self.dataTable.cellClicked.connect(self.highlight_from_table)  # Connect cell click to highlight function
    #     self.dataTable.setContextMenuPolicy(Qt.CustomContextMenu)  # Enable custom context menu
    #     self.dataTable.customContextMenuRequested.connect(self.show_context_menu)  # Connect context menu request to handler

    #     self.saveButton = QPushButton("Save Data", self)
    #     self.saveButton.clicked.connect(self.save_data)
    #     self.rightPanel.addWidget(self.saveButton)
    
    def setup_right_panel(self):
        # Create a QWidget to hold the right panel layout
        self.rightPanelWidget = QWidget(self)
        self.rightPanelLayout = QVBoxLayout(self.rightPanelWidget)

        # Add class section at the top
        classLabel = QLabel("Class:", self)
        self.rightPanelLayout.addWidget(classLabel)
        
        # Input field for new class
        self.classInput = QLineEdit(self)
        self.classInput.setPlaceholderText("Enter new class name")
        self.rightPanelLayout.addWidget(self.classInput)
        
        # Button to add new class
        self.addClassButton = QPushButton("Add Class", self)
        self.addClassButton.clicked.connect(self.add_new_class)
        self.rightPanelLayout.addWidget(self.addClassButton)
        
        # Class list widget
        self.classListWidget = QListWidget(self)
        self.classListWidget.addItems(["None"])  # Predefined classes
        self.rightPanelLayout.addWidget(self.classListWidget)

        # Data Table
        self.dataTable = QTableWidget(self)
        self.dataTable.setColumnCount(5)
        self.dataTable.setHorizontalHeaderLabels(["Index", "Start X", "Start Y", "End X", "End Y"])
        self.dataTable.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.rightPanelLayout.addWidget(self.dataTable)

        self.dataTable.cellClicked.connect(self.highlight_from_table)
        self.dataTable.setContextMenuPolicy(Qt.CustomContextMenu)
        self.dataTable.customContextMenuRequested.connect(self.show_context_menu)

        # Save Button
        self.saveButton = QPushButton("Save Data", self)
        self.saveButton.clicked.connect(self.save_data)
        self.rightPanelLayout.addWidget(self.saveButton)

        # Add right panel to the main layout
        self.rightPanel.addWidget(self.rightPanelWidget)

    
