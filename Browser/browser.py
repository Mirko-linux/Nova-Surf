import os
import json
import requests
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QToolBar, QAction, QLineEdit,
    QVBoxLayout, QWidget, QLabel, QHBoxLayout, QDialog, QComboBox, QPushButton,
    QMessageBox, QMenuBar)
from PyQt5.QtWidgets import QTabBar
from PyQt5.QtCore import QUrl, Qt
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtGui import QIcon, QPixmap


class Browser(QMainWindow):
    def __init__(self):
        super().__init__()
        print("Nova Surf avviato correttamente!")
        self.setWindowTitle("Nova Surf")
        self.setGeometry(100, 100, 1200, 800)

        self.search_engine = "DuckDuckGo"
        self.theme = "light"
        self.search_engines = {
            "DuckDuckGo": "https://duckduckgo.com/?q=",
            "Google": "https://www.google.com/search?q=",
            "Bing": "https://www.bing.com/search?q="
        }

        self.init_ui()

    def init_ui(self):
        # Header con logo e titolo
        title_layout = QHBoxLayout()
        logo_label = QLabel(self)
        logo_path = "photo_2025-04-09_11-31-55.png"
        logo_pixmap = QPixmap(logo_path)
        logo_label.setPixmap(logo_pixmap)
        logo_label.setFixedSize(32, 32)
        logo_label.setScaledContents(True)

        title_label = QLabel("Nova Surf", self)
        title_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #00aaff;")
        title_label.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)

        title_layout.addWidget(logo_label)
        title_layout.addSpacing(10)
        title_layout.addWidget(title_label)
        title_layout.addStretch()

        # Menu bar
        menu_bar = QMenuBar(self)
        self.setMenuBar(menu_bar)
        estensioni_menu = menu_bar.addMenu("Estensioni")

        servizi_action = QAction("Servizi Leonia+", self)
        servizi_action.triggered.connect(self.open_leonia_extension)
        estensioni_menu.addAction(servizi_action)

        gestore_action = QAction("🧩 Gestore Estensioni", self)
        gestore_action.setEnabled(False)
        estensioni_menu.addAction(gestore_action)

        title_widget = QWidget()
        title_widget.setLayout(title_layout)

        # Tab widget
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(False)  # Disabilita X standard
        self.tabs.currentChanged.connect(self.on_tab_changed)

        # Layout principale
        main_layout = QVBoxLayout()
        main_layout.addWidget(title_widget)
        main_layout.addWidget(self.tabs)

        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

        # Barra degli strumenti
        nav_bar = QToolBar()
        self.addToolBar(Qt.TopToolBarArea, nav_bar)

        self.address_bar = QLineEdit(self)
        self.address_bar.returnPressed.connect(self.navigate_to_url)
        nav_bar.addWidget(self.address_bar)

        nav_bar.addAction(QAction("◁ Indietro", self, triggered=self.navigate_back))
        nav_bar.addAction(QAction("▷ Avanti", self, triggered=self.navigate_forward))
        nav_bar.addAction(QAction("🔄 Ricarica", self, triggered=self.reload_page))
        nav_bar.addAction(QAction("🏠 Home", self, triggered=self.load_home))
        nav_bar.addAction(QAction("⚙ Impostazioni", self, triggered=self.open_settings))
        nav_bar.addAction(QAction("🛒", self, triggered=self.open_store))

        self.new_tab()

    def new_tab(self, url=None, is_real=True):
        # Rimuove la scheda "+" se esiste
        if self.tabs.count() > 0 and self.tabs.tabText(self.tabs.count() - 1) == "+":
            self.tabs.removeTab(self.tabs.count() - 1)

        if is_real:
            browser = QWebEngineView()
            index = self.tabs.addTab(browser, "Nuova Scheda")
            self.tabs.setCurrentIndex(index)
            self.load_home(browser)

            # X nera personalizzata
            close_btn = QPushButton("✖")
            close_btn.setStyleSheet("border: none; color: black; padding: 0px;")
            close_btn.clicked.connect(self.make_close_tab_handler(close_btn))
            self.tabs.tabBar().setTabButton(index, QTabBar.RightSide, close_btn)

        else:
            dummy = QWidget()
            self.tabs.addTab(dummy, "+")

        # Aggiungi scheda "+" sempre alla fine
        if self.tabs.tabText(self.tabs.count() - 1) != "+":
            self.tabs.addTab(QWidget(), "+")
            self.tabs.setTabEnabled(self.tabs.count() - 1, True)

    def make_close_tab_handler(self, button):
        def handler():
            for i in range(self.tabs.count()):
                if self.tabs.tabBar().tabButton(i, QTabBar.RightSide) == button:
                    self.close_tab(i)
                    break
        return handler

    def on_tab_changed(self, index):
        if self.tabs.tabText(index) == "+":
            self.new_tab()

    def close_tab(self, index):
        if self.tabs.count() > 1:
            self.tabs.removeTab(index)

    def navigate_to_url(self):
        url = self.address_bar.text()
        if not url.startswith("http"):
            url = self.search_engines[self.search_engine] + url
        self.tabs.currentWidget().setUrl(QUrl(url))

    def navigate_back(self):
        self.tabs.currentWidget().back()

    def navigate_forward(self):
        self.tabs.currentWidget().forward()

    def reload_page(self):
        self.tabs.currentWidget().reload()

    def open_store(self):
        store_url = QUrl("https://67f56a9cffc8b818ac192668--novasurfstore.netlify.app/")
        self.tabs.currentWidget().setUrl(store_url)
        self.tabs.setTabText(self.tabs.currentIndex(), "🛒 Store")

    def open_leonia_extension(self):
        ext_path = os.path.abspath("/home/Mirko/Documenti/Servizi Leonia+/popup.html")
        if os.path.exists(ext_path):
            url = QUrl.fromLocalFile(ext_path)
            self.tabs.currentWidget().setUrl(url)
            self.tabs.setTabText(self.tabs.currentIndex(), "Leonia+")
        else:
            QMessageBox.warning(self, "Errore", f"File non trovato: {ext_path}")

    def open_settings(self):
        self.settings_window = SettingsWindow(self)
        self.settings_window.settings_applied.connect(self.apply_settings)
        self.settings_window.show()

    def apply_settings(self, search_engine, theme):
        self.search_engine = search_engine
        self.theme = theme
        self.apply_theme()

    def apply_theme(self):
        if self.theme == "scuro":
            self.setStyleSheet("""
                QMainWindow { background-color: #121212; color: white; }
                QLabel, QLineEdit { color: white; }
                QToolBar { background-color: #1f1f1f; }
            """)
        else:
            self.setStyleSheet("")

    def fetch_news(self):
        api_key = 'fc89b08052684126a744651190bfdafa'
        url = f"https://newsapi.org/v2/everything?q=italia&sortBy=publishedAt&language=it&apiKey={api_key}"
        try:
            response = requests.get(url)
            if response.status_code == 200:
                articles = response.json().get('articles', [])
                print("Notizie ricevute:", articles)  # Debug: controlla le notizie ricevute
                if not articles:
                    return "<p>Nessuna notizia trovata al momento.</p>"
                news_content = ""
                for article in articles[:5]:
                    news_content += f'<a href="{article["url"]}" target="_blank">{article["title"]}</a><br><br>'
                return news_content
            else:
                return "<p>Errore nel caricamento delle notizie.</p>"
        except Exception as e:
            return f"<p>Errore: {e}</p>"

    def load_home(self, browser=None):
        print("Caricamento della home...")
        if browser is None:
            browser = self.tabs.currentWidget()
        
        search_url = self.search_engines[self.search_engine]
        news_content = self.fetch_news()

        home_html = f"""
        <html>
        <head>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    text-align: center;
                    padding-top: 50px;
                }}
                h1 {{
                    font-size: 2.5em;
                    color: #00aaff;
                }}
                .search-bar {{
                    margin-top: 20px;
                    width: 50%;
                    padding: 10px;
                    font-size: 1.2em;
                    border-radius: 5px;
                    border: 1px solid #ccc;
                }}
                .news {{
                    margin-top: 40px;
                    font-size: 1.2em;
                    max-width: 800px;
                    margin-left: auto;
                    margin-right: auto;
                    text-align: left;
                }}
                .news-title {{
                    font-size: 1.5em;
                    font-weight: bold;
                    color: #333;
                    margin-bottom: 15px;
                }}
                .news a {{
                    text-decoration: none;
                    color: #0077cc;
                    display: block;
                    margin-bottom: 5px;
                    font-size: 1.1em;
                    font-weight: bold;
                }}
                .news a:hover {{
                    text-decoration: underline;
                }}
            </style>
        </head>
        <body>
            <h1>Nova Surf</h1>
            <input class="search-bar" type="text" placeholder="Cerca..." id="searchBar" onkeydown="search(event)">
            <script>
                function search(event) {{
                    if (event.key === "Enter") {{
                        var query = document.getElementById("searchBar").value;
                        window.location.href = "{search_url}" + query;
                    }}
                }}
            </script>
            <div class="news">
                <div class="news-title">Leonia+ Notizie</div>
                {news_content}
            </div>
        </body>
        </html>
        """

        print("HTML pronto. Ora impostiamo la pagina.")

        if isinstance(browser, QWebEngineView):
            browser.setHtml(home_html)
            index = self.tabs.indexOf(browser)
            self.tabs.setTabText(index, "Home")
            print("HTML impostato nella scheda.")
        else:
            print("Errore: Il browser non è del tipo corretto.")


class SettingsWindow(QDialog):
    settings_applied = pyqtSignal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Impostazioni")
        self.setGeometry(400, 200, 300, 200)

        self.search_engine_combo = QComboBox(self)
        self.search_engine_combo.addItem("DuckDuckGo")
        self.search_engine_combo.addItem("Google")
        self.search_engine_combo.addItem("Bing")

        self.theme_combo = QComboBox(self)
        self.theme_combo.addItem("Chiaro")
        self.theme_combo.addItem("Scuro")

        apply_button = QPushButton("Applica", self)
        apply_button.clicked.connect(self.apply_settings)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Motore di ricerca"))
        layout.addWidget(self.search_engine_combo)
        layout.addWidget(QLabel("Tema"))
        layout.addWidget(self.theme_combo)
        layout.addWidget(apply_button)

    def apply_settings(self):
        search_engine = self.search_engine_combo.currentText()
        theme = self.theme_combo.currentText().lower()
        self.settings_applied.emit(search_engine, theme)
        self.accept()


if __name__ == '__main__':
    app = QApplication([])
    window = Browser()
    window.show()
    app.exec_()

