import os
import json
import requests
from PyQt5.QtWidgets import QToolButton, QMenu, QMenuBar
from PyQt5.QtWidgets import QLabel, QHBoxLayout, QApplication, QMainWindow, QTabWidget, QToolBar, QAction, QLineEdit, QVBoxLayout, QWidget, QDialog, QComboBox, QPushButton, QMessageBox
from PyQt5.QtCore import QUrl, Qt
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtGui import QIcon, QPixmap


class Browser(QMainWindow):
    def __init__(self):
        super().__init__()
        print("Nova Surf avviato correttamente!")

        self.setWindowTitle("Nova Surf")
        self.setGeometry(100, 100, 1200, 800)

        title_layout = QHBoxLayout()
        logo_path = "photo_2025-04-09_11-31-55.png"
        print(f"Path immagine: {os.path.abspath(logo_path)}")

        logo_label = QLabel(self)
        logo_pixmap = QPixmap(logo_path)
        if logo_pixmap.isNull():
            print("Errore nel caricamento dell'immagine!")
        else:
            print("Immagine caricata correttamente!")

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
        menu_bar = QMenuBar(self)
        self.setMenuBar(menu_bar)
        
        estensioni_menu = menu_bar.addMenu("Estensioni")

        servizi_action = QAction("Servizi Leonia+", self)
        servizi_action.triggered.connect(self.open_leonia_extension)
        estensioni_menu.addAction(servizi_action)

        gestore_action = QAction("🧩 Gestore Estensioni", self)
        gestore_action.setEnabled(False)  # Disabilitato perché non ancora implementato
        estensioni_menu.addAction(gestore_action)


        title_widget = QWidget()
        title_widget.setLayout(title_layout)

        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)

        main_layout = QVBoxLayout()
        main_layout.addWidget(title_widget)
        main_layout.addWidget(self.tabs)

        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

        nav_bar = QToolBar()
        self.addToolBar(Qt.TopToolBarArea, nav_bar)

        

        self.address_bar = QLineEdit(self)
        self.address_bar.returnPressed.connect(self.navigate_to_url)
        nav_bar.addWidget(self.address_bar)

        self.back_btn = QAction("◁ Indietro", self)
        self.back_btn.triggered.connect(self.navigate_back)
        nav_bar.addAction(self.back_btn)

        self.forward_btn = QAction("▷ Avanti", self)
        self.forward_btn.triggered.connect(self.navigate_forward)
        nav_bar.addAction(self.forward_btn)

        self.reload_btn = QAction("🔄 Ricarica", self)
        self.reload_btn.triggered.connect(self.reload_page)
        nav_bar.addAction(self.reload_btn)

        self.home_btn = QAction("🏠 Home", self)
        self.home_btn.triggered.connect(self.load_home)
        nav_bar.addAction(self.home_btn)

        self.settings_btn = QAction("⚙ Impostazioni", self)
        self.settings_btn.triggered.connect(self.open_settings)
        nav_bar.addAction(self.settings_btn)

        self.extension_btn = QAction("🧩 Gestore Estensioni", self)
        self.extension_btn.triggered.connect(self.open_leonia_extension)
        nav_bar.addAction(self.extension_btn)

        new_tab_btn = QAction("➕ Nuova Scheda", self)
        new_tab_btn.triggered.connect(self.new_tab)
        nav_bar.addAction(new_tab_btn)

        store_btn = QAction("🛒", self)
        store_btn.triggered.connect(self.open_store)
        nav_bar.addAction(store_btn)

        self.search_engine = "DuckDuckGo"
        self.theme = "light"
        self.search_engines = {
            "DuckDuckGo": "https://duckduckgo.com/?q=",
            "Google": "https://www.google.com/search?q=",
            "Bing": "https://www.bing.com/search?q="
        }

        self.home_url = QUrl("about:blank")
        self.new_tab()

    def open_settings(self):
        self.settings_window = SettingsWindow(self)
        self.settings_window.show()

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
        news_content = self.fetch_news()
        home_content = f"""
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
                        window.location.href = "https://duckduckgo.com/?q=" + query;
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
        if browser is None:
            browser = self.tabs.currentWidget()
        if isinstance(browser, QWebEngineView):
            browser.setHtml(home_content)
            index = self.tabs.indexOf(browser)
            self.tabs.setTabText(index, "Home")

    def new_tab(self):
        browser = QWebEngineView()
        self.tabs.addTab(browser, "Nuova Scheda")
        self.tabs.setCurrentWidget(browser)
        self.load_home(browser)

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

class SettingsWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Impostazioni")
        self.setGeometry(400, 200, 400, 200)

        self.search_engine = parent.search_engine
        self.theme = parent.theme
        self.search_engines = parent.search_engines

        layout = QVBoxLayout()

        self.search_combo = QComboBox(self)
        self.search_combo.addItems(self.search_engines.keys())
        self.search_combo.setCurrentText(self.search_engine)
        layout.addWidget(QLabel("Scegli motore di ricerca:"))
        layout.addWidget(self.search_combo)

        self.theme_combo = QComboBox(self)
        self.theme_combo.addItems(["Chiaro", "Scuro"])
        self.theme_combo.setCurrentText("Scuro" if self.theme == "scuro" else "Chiaro")
        layout.addWidget(QLabel("Scegli tema:"))
        layout.addWidget(self.theme_combo)

        self.apply_btn = QPushButton("Applica", self)
        self.apply_btn.clicked.connect(self.apply_changes)
        layout.addWidget(self.apply_btn)

        self.setLayout(layout)

    def apply_changes(self):
        selected_search_engine = self.search_combo.currentText()
        selected_theme = self.theme_combo.currentText().lower()
        self.parent().search_engine = selected_search_engine
        self.parent().theme = selected_theme
        self.parent().apply_theme()
        self.accept()


if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)
    window = Browser()
    window.show()
    sys.exit(app.exec_())

