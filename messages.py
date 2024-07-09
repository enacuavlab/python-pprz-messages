#!/usr/bin/env python3

# Copyright (C) 2024 Mael FEURGARD <mael.feurgard@enac.fr>
# 
# This file is part of messages_python.
# 
# messages_python is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# messages_python is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with messages_python.  If not, see <https://www.gnu.org/licenses/>.

import typing

from msgRecord.ivyRecorder import IvyRecorder

from PyQt5.QtWidgets import QWidget,QMainWindow,QApplication,\
                            QVBoxLayout,QTabWidget
                            

from PyQt5.QtCore import Qt,pyqtSlot

from messagesWidget import MessagesWidget


class MessagesMain(QTabWidget):
    def __init__(self, ivy:IvyRecorder,parent: QWidget | None = None) -> None:
        super().__init__(parent)
        
        self.ivyRecorder = ivy
        
        self.ivyRecorder.new_sender.connect(self.__newSender)
        self.setTabsClosable(False)
        
        self.currentChanged.connect(self.__pauseUnfocused)
        
    @pyqtSlot(int)
    def __newSender(self,id:int):
        w = MessagesWidget(self.ivyRecorder,id,self)
        index = self.addTab(w,f"Id: {id}")
        
        w.pauseUpdates(index != self.currentIndex())
        
        
    @pyqtSlot(int)
    def __pauseUnfocused(self,current:int):
        for t in range(self.count()):
            msgw:MessagesWidget = self.widget(t)
            msgw.pauseUpdates(current != t)
        



if __name__ == "__main__":
    app = QApplication([])
    app.setApplicationName("messages")
    
    ivy = IvyRecorder(buffer_size=1)
            
    window = MessagesMain(ivy,None)
    window.setWindowTitle("Paparazzi link Messages")
    
    app.aboutToQuit.connect(ivy.stop)
    
    window.show()
    app.exec()