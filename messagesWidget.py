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

import time

from msgRecord.ivyRecorder import IvyRecorder


from PyQt5.QtWidgets import QWidget,QMainWindow,QApplication,\
                            QVBoxLayout
                            

from PyQt5.QtCore import Qt

from messagesFilter import MessagesFilter
from messagesView import MessagesView



class MessagesWidget(QWidget):
    def __init__(self, ivy:IvyRecorder,sender_id:int, parent: QWidget | None = None,flags: Qt.WindowFlags | Qt.WindowType = Qt.WindowType.Widget) -> None:
        super().__init__(parent, flags)
        
        self.filterWidget = MessagesFilter(self)
        self.viewWiget = MessagesView(ivy,sender_id,self)
        
        self.vLayout =  QVBoxLayout(self)
        self.vLayout.addWidget(self.filterWidget)
        self.vLayout.addWidget(self.viewWiget)
        
        self.setLayout(self.vLayout)
        
        self.filterWidget.filteringChanged.connect(self.viewWiget.proxyModel.setFilterRegularExpression)
        self.filterWidget.filteringDone.connect(self.viewWiget.safeExpandAll)
        
        self.filterWidget.pinFiltering.connect(self.viewWiget.proxyModel.setCheckedOnly)

    def pauseUpdates(self,b:bool):
        self.viewWiget.backModel.pauseUpdates(b)

        
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser("Debug MessagesView")
    parser.add_argument('sender_id',type=int,help="ID of the sender to record")
    
    args = parser.parse_args()
    
    app = QApplication([])
    
    ivy = IvyRecorder(buffer_size=1)
    sender_id = args.sender_id
    
    while not sender_id in ivy.known_senders.keys():
        try:
            print(f"Waiting for Id {sender_id}")
            time.sleep(0.1)
        except KeyboardInterrupt:
            ivy.stop()
            exit(0)
            
    window = MessagesWidget(ivy,sender_id,None)
    
    app.aboutToQuit.connect(ivy.stop)
    
    window.show()
    app.exec()