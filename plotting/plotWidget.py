#!/usr/bin/env python3

import typing
import dataclasses

import numpy as np
import time


import pyqtgraph as pg

from PyQt5.QtCore import Qt,pyqtSlot,QTimer,QEvent
from PyQt5.QtGui import QDropEvent,QDragEnterEvent
from PyQt5.QtWidgets import QSplitter,QMainWindow,QApplication,QWidget
                            
from msgRecord.messageLog import MessageLog,MessageIndex,FieldIndex
from msgRecord.ivyRecorder import IvyRecorder

from pprzlink.message import PprzMessage

# Fetch color palette from: http://tsitsul.in/blog/coloropt/
# Bright:

BRIGHT_RGBS = [(239,230,69),(233,53,161),(0,227,255),(225,86,44),(83,126,255),(0,203,133),(238,238,238)]

HIGHLIGHT_COUNT = 3
ALPHA_START = 100
ALPHA_STOP = 50
LINEWIDTH_START = 1
LINEWIDTH_STOP = 8


@dataclasses.dataclass
class FieldPlotInfo:
    index:FieldIndex
    color:tuple[int,int,int]
    plotItem:pg.PlotDataItem
    rescale:float = 1.
    
    _highlightItems:list[pg.PlotDataItem] = dataclasses.field(init=False)
    
    def __post_init__(self):
        self._highlightItems = []
        
        alphas = np.linspace(ALPHA_START,ALPHA_STOP,HIGHLIGHT_COUNT)
        lws = np.linspace(LINEWIDTH_START,LINEWIDTH_STOP,HIGHLIGHT_COUNT)
        
        for alpha, lw in zip(alphas, lws):

                pen = pg.mkPen(color=(self.color[0],self.color[1],self.color[2],alpha),
                               width=lw,
                               connect="finite")


                self._highlightItems.append(pg.PlotDataItem([], [],
                                            pen=pen))
        
    
    @staticmethod
    def from_MIMEtxt(txt:str, line_id:int) -> tuple[list,int]:
        
        # Expected format for field description:
        # "{sender}:{class_name}:{msg_name}:{field_name}:{field_scale}"
        # OR, if the field is of array type (range is both inclusive):
        # "{sender}:{class_name}:{msg_name}:{field_name}[{array_range}]:{field_scale}"
        split = txt.split(':')
        
        try:
            assert len(split) >= 4
        except AssertionError as e:
            print(f"Unexpected splitted length: {len(split)} (instead of at least 4)")
            print(f"Split is:\n{split}\nText is:\n{txt}")
            raise e
        
        sender = int(split[0])
        class_name = split[1]
        msg_name = split[2]
        field_info = split[3]
        # field_scale = float(split[4])
        
        
        msg = PprzMessage(class_name,msg_name)
        
        if '[' in field_info:
            # This is an array field
            field_info = field_info.split('[')
            field_name = field_info[0]
            array_range_txt = field_info[1][:-1] # Remove trailing ']'
            if '-' in array_range_txt:
                art_split = array_range_txt.split('-')
                index_range = range(int(art_split[0]),int(art_split[1])+1)
            else:
                index_range = [int(array_range_txt)]
            
        else:
            field_name = field_info
            index_range = [None]
            
        field = msg.get_full_field(field_name)
        if field.alt_unit_coef is not None:
            field_scale = field.alt_unit_coef
            field_unit = field.alt_unit
        else:
            field_scale = 1.
            field_unit = field.unit
            

        output = []
        for e in index_range:
            index = FieldIndex.from_ints(sender,msg.class_id,msg.msg_id,field_name,e)
            
            title = f"{sender}:{class_name}:{msg_name}:{field_name}" + ("" if e is None else f"[{e}]") + ("" if field_unit is None else f" ({field_unit})")
            
            color = BRIGHT_RGBS[line_id % len(BRIGHT_RGBS)]
            pltitem = pg.PlotDataItem([],[],
                            title=title,
                            name=title,
                            pen=color)
            
            line_id = (line_id+1) % len(BRIGHT_RGBS)
            
            pltitem.setFlag(pltitem.GraphicsItemFlag.ItemIsSelectable,True)
            pltitem.setCurveClickable(True,12)
            pltitem.sigClicked.connect(lambda _ : pltitem.setSelected(True))
            
            output.append(FieldPlotInfo(index,color,pltitem,field_scale))
            
        return output,line_id
            
        
    def getMIMEtxt(self) -> str:
        sender = self.index.sender_id
        class_name = self.msgLog.msg_class()
        msg_name = self.msgLog.msg_name()
        
        field_name = self.index.field
        
        full_field = self.msgLog.get_full_field(field_name)
        field_scale = full_field.alt_unit_coef
        if field_scale is None:
            field_scale = 1.
        
        
        if self.index.array_index is None:
            txt = f"{sender}:{class_name}:{msg_name}:{field_name}:{field_scale}"
        else:
            txt = f"{sender}:{class_name}:{msg_name}:{field_name}[{self.index.array_index}]:{field_scale}"
        
        return txt

    
    def highlightCurves(self) -> list[pg.PlotCurveItem]:
        return self._highlightItems


class PlotWidget(pg.PlotWidget):
    def __init__(self, ivy:IvyRecorder, parent=None, background='default', **kargs):
        super().__init__(parent, background, None, **kargs)
        
        self.ivyRecorder = ivy
        
        self.setAcceptDrops(True)
        
        self.plotItem.setAcceptDrops(True)
        self.plotItem.dropEvent = lambda e : self.dropEvent(e)
        
        self.plotItem.addLegend()
        
        self.timer = QTimer()
        self.timer.timeout.connect(self.update)
        
        self.timerDt = 500 # Time between updates, in ms
        
        self.timer.start(self.timerDt) 
        
        ax_item:pg.AxisItem = self.plotItem.getAxis('bottom')
        ax_item.setLabel(text='Time since reception',units='s')
        
        
        self.__line_count = 0
        
        
        # Map : sender_id -> class_id -> message_id -> field_name -> FieldPlotInfo
        self.plotItemMap:dict[int,dict[int,dict[int,dict[str,FieldPlotInfo]]]] = dict()
    
    def getPlotItem(self,index:FieldIndex):
        return self.plotItemMap[index.sender_id][index.class_id][index.message_id][index.field]
    
    def pauseUpdates(self,b:bool):
        if b:
            self.timer.stop()
        else:
            self.timer.start()

    @pyqtSlot()
    def update(self):
        now = time.time_ns()
        
        for s,sd in self.plotItemMap.items():
            for c,cd in sd.items():
                for m,md in cd.items():
                    mIndex = MessageIndex(s,c,m)
                    
                    try:
                        msgLog = self.ivyRecorder.getMessage(mIndex)
                    except KeyError:
                        continue
                    
                    times = []
                    
                    data:dict[str,list] = dict()
                    for f in md.keys():
                        data[f] = []
                    
                    for mm in msgLog.queue:
                        times.append((mm.timestamp-now)/10**9)
                        for f,l in data.items():
                            l.append(mm[f])
                    
                    for f,p in md.items():
                        p.plotItem.setData(times,np.asarray(data[f])*p.rescale)
                        if p.plotItem.isSelected():
                            for hp in p.highlightCurves():
                                hp.setData(times,np.asarray(data[f])*p.rescale)
                        else:
                            for hp in p.highlightCurves():
                                hp.setData([],[])
                        
    ########## MIME aspects (Drag N Drop)  ##########
    
    def dragEnterEvent(self,e:QDragEnterEvent):
        mimedata = e.mimeData()
        
        if (mimedata.hasText()):
            txt = mimedata.text()
            
            if ':' in txt:
                # e.acceptProposedAction()
                e.accept()

    
    def dropEvent(self,e:QDropEvent):
        mimedata = e.mimeData()
                
        # Expected format for field description:
        # "{sender}:{class_name}:{msg_name}:{field_name}:{field_scale}"
        # OR, if the field is of array type:
        # "{sender}:{class_name}:{msg_name}:{field_name}[{array_range}]:{field_scale}"
        txt = mimedata.text()
        
        pltInfo_lst,self.__line_count = FieldPlotInfo.from_MIMEtxt(txt,self.__line_count)
                
        for p in pltInfo_lst:
            p:FieldPlotInfo
            try:
                pp = self.getPlotItem(p.index)
                continue
            except KeyError:
                try:
                    s_dict = self.plotItemMap[p.index.sender_id]
                except KeyError:
                    self.plotItemMap[p.index.sender_id] = dict()
                    s_dict = self.plotItemMap[p.index.sender_id]
                
                try:
                    c_dict = s_dict[p.index.class_id]
                except KeyError:
                    s_dict[p.index.class_id] = dict()
                    c_dict = s_dict[p.index.class_id]
                    
                try:
                    m_dict = c_dict[p.index.message_id]
                except KeyError:
                    c_dict[p.index.message_id] = dict()
                    m_dict = c_dict[p.index.message_id]
                    
                m_dict[p.index.field] = p
                
                self.addItem(p.plotItem)

            self.ivyRecorder.recordMessage(p.index.sender_id,p.index.pprzMsg())
                
        self.update()
        
        e.acceptProposedAction()
        