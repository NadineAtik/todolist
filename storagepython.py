import sys
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import QPushButton, QWidget, QGridLayout, QLineEdit, QComboBox, QTableView, QVBoxLayout, QMessageBox, QFileDialog
from PyQt5.QtCore import QAbstractTableModel, Qt
from datetime import datetime
import sqlite3
import firebase_admin
from firebase_admin import credentials, firestore, db, storage
import os
import shutil

# Initialiser Firebase
cred = credentials.Certificate('delme-a9b52-firebase-adminsdk-3zef6-336080a7c6.json')
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://delme-a9b52-default-rtdb.asia-southeast1.firebasedatabase.app',
    'storageBucket': 'delme-a9b52.appspot.com'
})
db_realtime = db.reference()
db_firestore = firestore.client()
bucket = storage.bucket()

# Connexion à la base de données SQLite
conn = sqlite3.connect('todolist1.db')
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS todo_list (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task TEXT,
    status TEXT,
    lienfichier TEXT,
    lienlocale TEXT,
    date TEXT,
    heure TEXT,
    lesdeux TEXT,
    timestamp INTEGER)''')
conn.commit()

# Modèle personnalisé dérivé de QAbstractTableModel pour gérer les données du tableau
class TodoTableModel(QAbstractTableModel):
    def __init__(self, data=[], headers=[]):
        super().__init__()
        self._data = data
        self.headers = headers

    def rowCount(self, parent=QtCore.QModelIndex()):
        return len(self._data)

    def columnCount(self, parent=QtCore.QModelIndex()):
        return len(self.headers)

    def data(self, index, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            return self._data[index.row()][index.column()]

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return self.headers[section]
            else:
                return str(section)

# Classe principale de l'application
class ContentMain(QWidget):
    def __init__(self):
        super().__init__()
        self._create()
        self._layout()
        self._configure()
        self.load_data()

    def _create(self):
        self.save = QPushButton("Sauvegarder")
        self.ajouter = QPushButton("ajouter")
        self.editer = QPushButton("Editer")
        self.eliminer = QPushButton("Eliminer")
        self.nettoyer_tout = QPushButton("Nettoyer tout")
        self.telecharger_fichier = QPushButton("telecharger fichier")
        self.telecharger = QPushButton("Download")  # Nouveau bouton de téléchargement
        self.task_line_edit = QLineEdit(self)
        self.status_combobox = QComboBox(self)
        self.status_combobox.addItems(["done", "notdone", "inprocess"])
        self.tasks_table = QTableView(self)
        self.model = TodoTableModel(headers=["Tâche", "Statut", "Lien Fichier", "Lien Local", "Date", "Heure"])
        self.tasks_table.setModel(self.model)

    def _layout(self):
        layout = QVBoxLayout(self)
        button_layout = QGridLayout()
        button_layout.addWidget(self.save, 0, 0)
        button_layout.addWidget(self.task_line_edit, 0, 1, 1, 2)
        button_layout.addWidget(self.status_combobox, 0, 3)
        button_layout.addWidget(self.telecharger_fichier, 0, 4)
        button_layout.addWidget(self.ajouter, 1, 0)
        button_layout.addWidget(self.editer, 1, 1)
        button_layout.addWidget(self.eliminer, 1, 2)
        button_layout.addWidget(self.nettoyer_tout, 1, 3)
        button_layout.addWidget(self.telecharger, 1, 4)  # Ajout du bouton de téléchargement
        layout.addLayout(button_layout)
        layout.addWidget(self.tasks_table)

    def _configure(self):
        self.ajouter.clicked.connect(self.add_task)
        self.editer.clicked.connect(self.edit_task)
        self.eliminer.clicked.connect(self.delete_task)
        self.nettoyer_tout.clicked.connect(self.clear_tasks)
        self.telecharger_fichier.clicked.connect(self.open_file_dialog)
        self.telecharger.clicked.connect(self.download_file)  # Connexion du bouton de téléchargement
        self.save.clicked.connect(self.save_data)

    def load_data(self):
        cursor.execute('SELECT task, status, lienfichier, lienlocale, date, heure FROM todo_list')
        rows = cursor.fetchall()
        self.model._data = rows
        self.model.layoutChanged.emit()

    def add_task(self, lien_fichier='', lien_locale=''):
        task = self.task_line_edit.text()
        status = self.status_combobox.currentText()
        now = datetime.now()
        date = now.strftime("%Y-%m-%d")
        heure = now.strftime("%H:%M")
        lesdeux = now.strftime("%Y-%m-%d %H:%M")
        timestamp = int(now.timestamp())
        if task:
            self.model._data.append([task, status, lien_fichier, lien_locale, date, heure])
            self.model.layoutChanged.emit()
            self.save_item_to_firebase(task, status, lien_fichier, lien_locale, date, heure, lesdeux, timestamp)
            self.save_item_to_sqlite(task, status, lien_fichier, lien_locale, date, heure, lesdeux, timestamp)

    def save_item_to_firebase(self, task, status, lien_fichier, lien_locale, date, heure, lesdeux, timestamp):
        db_firestore.collection('tasksCollection').add({
            'task': task,
            'status': status,
            'lien_fichier': lien_fichier,
            'lien_locale': lien_locale,
            'date': date,
            'heure': heure,
            'lesdeux': lesdeux,
            'timestamp': timestamp
        })
        db_realtime.child('todo_list').push({
            'task': task,
            'status': status,
            'lien_fichier': lien_fichier,
            'lien_locale': lien_locale,
            'date': date,
            'heure': heure,
            'lesdeux': lesdeux,
            'timestamp': timestamp
        })

    def save_item_to_sqlite(self, task, status, lien_fichier, lien_locale, date, heure, lesdeux, timestamp):
        cursor.execute('''INSERT INTO todo_list (task, status, lienfichier, lienlocale, date, heure, lesdeux, timestamp)
                          VALUES (?, ?, ?, ?, ?, ?, ?, ?)''', (task, status, lien_fichier, lien_locale, date, heure, lesdeux, timestamp))
        conn.commit()

    def open_file_dialog(self):
        file_dialog = QFileDialog()
        lien_fichier, _ = file_dialog.getOpenFileName(self, "Sélectionnez un fichier", "", "Tous les fichiers (*)")
        if lien_fichier:
            storage_path = os.path.join('storagedocument', os.path.basename(lien_fichier))
            os.makedirs('storagedocument', exist_ok=True)
            shutil.copy(lien_fichier, storage_path)
            public_url = self.upload_file_to_firebase(lien_fichier)  # Enlever l'horodatage ici
            self.add_task(os.path.basename(lien_fichier), storage_path)  # Utiliser seulement le nom du fichier

    def upload_file_to_firebase(self, local_file_path):
        try:
            firebase_file_name = os.path.basename(local_file_path)  # Utiliser seulement le nom du fichier
            blob = bucket.blob(firebase_file_name)
            blob.upload_from_filename(local_file_path)
            blob.make_public()
            return blob.public_url
        except Exception as e:
            print(f"Erreur lors du téléchargement du fichier : {e}")
            return None

    def download_file(self):
        index = self.tasks_table.currentIndex()
        if not index.isValid():
            self.show_messagebox("Erreur", "Veuillez sélectionner une tâche avec un fichier à télécharger.")
            return
        row = index.row()
        lien_fichier = self.model._data[row][2]
        if lien_fichier:
            confirmation = self.show_confirmation_dialog("Confirmation", "Es-tu sûr de vouloir télécharger le fichier ?")
            if confirmation == QMessageBox.Yes:
                # Emplacement par défaut pour télécharger le fichier
                save_path = os.path.join(os.path.expanduser('~'), 'Downloads', os.path.basename(lien_fichier))
                self.download_file_from_firebase(lien_fichier, save_path)
        else:
            self.show_messagebox("Erreur", "Aucun lien de fichier disponible pour cette tâche.")

    def download_file_from_firebase(self, firebase_file_name, save_path):
        try:
            blob = bucket.blob(firebase_file_name)
            blob.download_to_filename(save_path)
            self.show_messagebox("Succès", f"Le fichier a été téléchargé avec succès dans {save_path}.")
        except Exception as e:
            self.show_messagebox("Erreur", f"Erreur lors du téléchargement du fichier : {e}")

    def show_confirmation_dialog(self, title, message):
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Question)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        return msg_box.exec_()

    def edit_task(self):
        index = self.tasks_table.currentIndex()
        if not index.isValid():
            self.show_messagebox("Erreur", "Veuillez sélectionner une tâche à éditer.")
            return
        row = index.row()
        task = self.model._data[row][0]
        new_task, ok = QtWidgets.QInputDialog.getText(self, "Editer Tâche", "Tâche:", QtWidgets.QLineEdit.Normal, task)
        if ok and new_task:
            self.model._data[row][0] = new_task
            self.model.layoutChanged.emit()

    def delete_task(self):
        index = self.tasks_table.currentIndex()
        if not index.isValid():
            self.show_messagebox("Erreur", "Veuillez sélectionner une tâche à supprimer.")
            return
        row = index.row()
        task_id = self.model._data[row][0]  # Assurez-vous que l'ID est dans la première colonne
        self.model._data.pop(row)
        self.model.layoutChanged.emit()
        cursor.execute('DELETE FROM todo_list WHERE id = ?', (task_id,))
        conn.commit()

    def clear_tasks(self):
        self.model._data.clear()
        self.model.layoutChanged.emit()
        cursor.execute('DELETE FROM todo_list')
        conn.commit()

    def save_data(self):
        for row in self.model._data:
            task, status, lien_fichier, lien_locale, date, heure = row
            now = datetime.now()
            lesdeux = now.strftime("%Y-%m-%d %H:%M")
            timestamp = int(now.timestamp())
            self.save_item_to_sqlite(task, status, lien_fichier, lien_locale, date, heure, lesdeux, timestamp)
            self.save_item_to_firebase(task, status, lien_fichier, lien_locale, date, heure, lesdeux, timestamp)
        self.show_messagebox("Succès", "Les données ont été sauvegardées.")

    def show_messagebox(self, title, message):
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Information)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.exec_()

# Point d'entrée de l'application
if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = ContentMain()
    window.show()
    sys.exit(app.exec_())
conn.close()