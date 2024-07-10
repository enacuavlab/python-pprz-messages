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

import pathlib

from msgRecord.ivyRecorder import IvyRecorder
from msgRecord.qtMessageModel import FilteredIvyModel,IvyModel,\
                                        FieldItem,SenderItem,MessageItem,MessageClassItem


from PyQt5.QtWidgets import QWidget,QApplication,\
                            QSizePolicy,QHeaderView,\
                            QTreeView,QVBoxLayout,QWidget,QTabWidget

from PyQt5.QtCore import Qt,QModelIndex,pyqtSlot


from messagesFilter import MessagesFilter

class MessagesView(QTreeView):
    def __init__(self, ivyModel:FilteredIvyModel,parent: QWidget | None = None) -> None:
        super().__init__(parent)
                
        self.ivyModel = ivyModel
        
        self.setModel(self.ivyModel)
        
        self.setSortingEnabled(True)
        self.sortByColumn(0,Qt.SortOrder.AscendingOrder)
        
        self.setSizeAdjustPolicy(QTreeView.SizeAdjustPolicy.AdjustToContents)
        self.sizePolicy().setHorizontalPolicy(QSizePolicy.Policy.Minimum)
        self.sizePolicy().setVerticalPolicy(QSizePolicy.Policy.Minimum)
        self.header().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        
        self.setWordWrap(False)
        
        self.doubleClicked.connect(self.__expandAllOnDoubleClick)
        self.model().rowsInserted.connect(self.__autoExpandTopItems)
        
        self.setSelectionBehavior(QTreeView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QTreeView.SelectionMode.SingleSelection)
        self.setDragDropMode(self.DragDropMode.DragOnly)
                        
        localdir =  pathlib.Path(__file__).parent
        
        style = """
QTreeView::indicator:unchecked{
    image: url(:/icons/pin/normal/16.png);
}

QTreeView::indicator:checked{
    image: url(:/icons/pin/active_straight/16.png);
}

QTreeView::indicator:indeterminate{
    image: url(:/icons/pin/active/16.png);
}

/* 
QTreeView::branch:has-siblings:!adjoins-item {
    border-image: url(:/images/vline.png) 0;
}
*/

QTreeView::branch:has-siblings:adjoins-item {
    border-image: url(:/images/branch-more.png) 0;
}

QTreeView::branch:!has-children:!has-siblings:adjoins-item {
    border-image: url(:/images/branch-end.png) 0;
}

QTreeView::branch:has-children:!has-siblings:closed,
QTreeView::branch:closed:has-children:has-siblings {
        border-image: none;
        image: url(:/images/branch-closed.png);
}

QTreeView::branch:open:has-children:!has-siblings,
QTreeView::branch:open:has-children:has-siblings  {
        border-image: none;
        image: url(:/images/branch-open.png);
}
                            """.replace('url(:',f'url({localdir}')
                        
        self.setStyleSheet(style)
          
    @pyqtSlot(QModelIndex)
    def __expandAllOnDoubleClick(self,index:QModelIndex):
        rootIndex =  index.sibling(index.row(),0)
        if self.isExpanded(rootIndex):
            self.collapse(rootIndex)
        else:
            self.expand(rootIndex)
            
    @pyqtSlot(QModelIndex,int,int)
    def __autoExpandTopItems(self,parent:QModelIndex,start:int,stop:int):
        if not(parent.isValid()):
            return
        
        if not(parent.parent().isValid()):
            if not(self.isExpanded(parent)):
                self.expand(parent)
    
    
class SenderMessagesView(MessagesView):
    def __init__(self, ivyModel:FilteredIvyModel,sender_id:int, parent: QWidget | None = None) -> None:
        super().__init__(ivyModel,parent)
        
        self.senderId = sender_id

        
        self.setRootIndex(self.ivyModel.getSenderIndex(sender_id))
        
        
    @pyqtSlot()
    def safeExpandAll(self):
        if self.model().messageCount(self.senderId) < 5:
            self.expandAll()



class MessagesWidget(QWidget):
    def __init__(self, ivy:IvyRecorder,ivyModel:IvyModel, filteredModel:FilteredIvyModel,parent: QWidget | None = None,flags: Qt.WindowFlags | Qt.WindowType = Qt.WindowType.Widget) -> None:
        super().__init__(parent, flags)
        
        self.filterWidget = MessagesFilter(self)
        
        self.ivy = ivy
        self.model = ivyModel
        self.filteredModel = filteredModel
        
        self.tabWidget = QTabWidget(self)
        self.tabWidget.setTabsClosable(False)
        
        self.vLayout =  QVBoxLayout(self)
        self.vLayout.addWidget(self.filterWidget)
        self.vLayout.addWidget(self.tabWidget)
        
        self.setLayout(self.vLayout)
        
        self.ivy.new_sender.connect(self.newSender)
        
    @pyqtSlot(int)
    def newSender(self,id:int):
        self.ivy.recordSender(id)
        self.model.updateTimes()
        
        newView = SenderMessagesView(self.filteredModel,id,self)
        
        self.filterWidget.filteringChanged.connect(newView.ivyModel.setFilterRegularExpression)
        self.filterWidget.filteringDone.connect(newView.safeExpandAll)
        
        self.filterWidget.pinFiltering.connect(newView.ivyModel.setCheckedOnly)
        
        self.tabWidget.addTab(newView,f"Sender {id}")

        
if __name__ == "__main__":
    
    app = QApplication([])
    
    ivy = IvyRecorder(buffer_size=1)
            
    window = MessagesWidget(ivy,None)
    
    app.aboutToQuit.connect(ivy.stop)
    
    window.show()
    app.exec()