#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LabSoft Desktop Entry Point."""

import sys
from PyQt6.QtWidgets import QApplication
from app.ui import style
from app.ui.login_dialog import sign_in_at_startup
from app.ui.main_window import MainWindow
from app.db import connection, queries as q

def main():
    app = QApplication(sys.argv)
    app.setApplicationName('LabSoft')
    app.setOrganizationName('MITHRA MEDICAL LABORATORY')
    
    # Initialize DB connection and apply clinical theme
    connection.connect()
    style.apply_theme(app, 'light')
    
    # Sign in dialog
    ok, user = sign_in_at_startup()
    if not ok or not user:
        sys.exit(0)
        
    win = MainWindow()
    win.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
