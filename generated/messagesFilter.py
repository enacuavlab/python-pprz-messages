# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui/messagesFilter.ui'
#
# Created by: PyQt5 UI code generator 5.15.6
#
# WARNING: Any manual changes made to this file will be lost when pyuic5 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_Form(object):
    def setupUi(self, Form):
        Form.setObjectName("Form")
        Form.resize(365, 94)
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout(Form)
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.filterFrame = QtWidgets.QFrame(Form)
        self.filterFrame.setObjectName("filterFrame")
        self.horizontalLayout = QtWidgets.QHBoxLayout(self.filterFrame)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.verticalLayout = QtWidgets.QVBoxLayout()
        self.verticalLayout.setObjectName("verticalLayout")
        self.multiSenderPinCheckBox = QtWidgets.QCheckBox(self.filterFrame)
        self.multiSenderPinCheckBox.setChecked(True)
        self.multiSenderPinCheckBox.setObjectName("multiSenderPinCheckBox")
        self.verticalLayout.addWidget(self.multiSenderPinCheckBox)
        self.pinCheckBox = QtWidgets.QCheckBox(self.filterFrame)
        self.pinCheckBox.setObjectName("pinCheckBox")
        self.verticalLayout.addWidget(self.pinCheckBox)
        self.horizontalLayout.addLayout(self.verticalLayout)
        self.filterLineEdit = QtWidgets.QLineEdit(self.filterFrame)
        self.filterLineEdit.setText("")
        self.filterLineEdit.setReadOnly(False)
        self.filterLineEdit.setClearButtonEnabled(True)
        self.filterLineEdit.setObjectName("filterLineEdit")
        self.horizontalLayout.addWidget(self.filterLineEdit)
        self.horizontalLayout_2.addWidget(self.filterFrame)

        self.retranslateUi(Form)
        QtCore.QMetaObject.connectSlotsByName(Form)

    def retranslateUi(self, Form):
        _translate = QtCore.QCoreApplication.translate
        Form.setWindowTitle(_translate("Form", "Form"))
        self.multiSenderPinCheckBox.setToolTip(_translate("Form", "While checked, pinning a message for any sender will attempt to the same message for all other senders."))
        self.multiSenderPinCheckBox.setText(_translate("Form", "Pin across senders"))
        self.pinCheckBox.setToolTip(_translate("Form", "While active, display only the pinned fields"))
        self.pinCheckBox.setText(_translate("Form", "Show only pinned"))
        self.filterLineEdit.setPlaceholderText(_translate("Form", "Search message/id/field (regex allowed)"))
