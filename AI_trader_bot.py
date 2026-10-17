# trader_bot.py
import os, sys, requests, re
from datetime import datetime
from urllib.request import getproxies
from urllib.parse import urlsplit, urlunsplit
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *
import database_manager as db, config, google.generativeai as genai
from ui_widgets import CandlestickWidget
import tg_poster, post_generator

# ... (Код GeminiWorker и SignalHistoryDialog без изменений) ...
try:
    if "СЮДА_ВСТАВЬТЕ" not in config.GOOGLE_API_KEY:
        # REST использует обычный HTTPS и совместим с локальным HTTP-прокси.
        for protocol, proxy_url in getproxies().items():
            parsed = urlsplit(proxy_url)
            if protocol in ("http", "https") and parsed.scheme == "https" and parsed.hostname in ("localhost", "127.0.0.1", "::1"):
                proxy_url = urlunsplit(parsed._replace(scheme="http"))
            if protocol in ("http", "https"):
                os.environ[protocol.upper() + "_PROXY"] = proxy_url
                os.environ[protocol + "_proxy"] = proxy_url
        genai.configure(api_key=config.GOOGLE_API_KEY, transport="rest");
        model = genai.GenerativeModel('gemini-3.8-flash')
    else:
        print("ПРЕДУПРЕЖДЕНИЕ: GOOGLE_API_KEY не указан в config.py"); model = None
except Exception as e:
    print(f"Ошибка конфигурации Gemini API: {e}"); model = None


class GeminiWorker(QObject):
    finished = pyqtSignal(dict);
    error = pyqtSignal(str)

    def __init__(self, symbol, data_string, parent=None):
        super().__init__(parent);
        self.symbol, self.data_string = symbol, data_string

    def run(self):
        try:
            if not model: self.error.emit("Модель Gemini не инициализирована."); return
            prompt = config.GEMINI_PROMPT_TEMPLATE.format(symbol=self.symbol, data=self.data_string)
            response = model.generate_content(prompt);
            text = response.text
            sl = float(re.search(r"Stop-Loss:\s*([\d\.]+)", text, re.IGNORECASE).group(1))
            tp1 = float(re.search(r"Take-Profit-1:\s*([\d\.]+)", text, re.IGNORECASE).group(1))
            tp2 = float(re.search(r"Take-Profit-2:\s*([\d\.]+)", text, re.IGNORECASE).group(1))
            self.finished.emit({'sl': sl, 'tp1': tp1, 'tp2': tp2})
        except (AttributeError, IndexError, ValueError):
            self.error.emit(f"Не удалось извлечь уровни из ответа Gemini:\n{text}")
        except Exception as e:
            self.error.emit(f"Произошла ошибка при запросе к Gemini: {e}")


class SignalHistoryDialog(QDialog):
    signal_selected = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent);
        self.setWindowTitle("История сигналов");
        self.setMinimumSize(450, 500)
        self.layout = QVBoxLayout(self);
        self.list_widget = QListWidget();
        self.layout.addWidget(self.list_widget)
        button_layout = QHBoxLayout()
        self.delete_button = QPushButton("Удалить");
        self.clear_all_button = QPushButton("Очистить всё");
        self.apply_button = QPushButton("Применить")
        self.apply_button.setStyleSheet("background-color: #2a9d8f; font-weight: bold;")
        self.delete_button.clicked.connect(self.delete_selected_signal);
        self.clear_all_button.clicked.connect(self.clear_all_history);
        self.apply_button.clicked.connect(self.apply_selection)
        button_layout.addWidget(self.delete_button);
        button_layout.addWidget(self.clear_all_button);
        button_layout.addStretch();
        button_layout.addWidget(self.apply_button)
        self.layout.addLayout(button_layout)
        self.load_history()

    def load_history(self):
        self.list_widget.clear()
        signals = db.load_signals()
        for signal in signals:
            tp2_text = f" | TP2: {signal.get('take_profit_2', 'N/A')}"
            item_text = (
                f"{signal['timestamp']} - {signal['symbol']} | SL: {signal['stop_loss']} | TP1: {signal['take_profit']}{tp2_text}")
            list_item = QListWidgetItem(item_text);
            list_item.setData(Qt.UserRole, signal);
            self.list_widget.addItem(list_item)

    def apply_selection(self):
        current_item = self.list_widget.currentItem()
        if not current_item: QMessageBox.warning(self, "Ошибка", "Пожалуйста, выберите сигнал для применения."); return
        signal_data = current_item.data(Qt.UserRole);
        self.signal_selected.emit(signal_data);
        self.accept()

    def delete_selected_signal(self):
        current_item = self.list_widget.currentItem()
        if not current_item: QMessageBox.warning(self, "Ошибка", "Пожалуйста, выберите сигнал для удаления."); return
        reply = QMessageBox.question(self, 'Подтверждение', 'Вы уверены?', QMessageBox.Yes | QMessageBox.No,
                                     QMessageBox.No)
        if reply == QMessageBox.Yes:
            signal_data = current_item.data(Qt.UserRole);
            db.delete_signal(signal_data['id']);
            self.load_history()

    def clear_all_history(self):
        reply = QMessageBox.question(self, 'Подтверждение', 'Вы уверены, что хотите ПОЛНОСТЬЮ очистить историю?',
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes: db.clear_all_signals(); self.load_history()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Анализатор криптовалют с Gemini AI");
        self.setGeometry(100, 100, 900, 750)
        self.setStyleSheet("""...""")  # Стили
        self.symbols, self.current_symbol = ['BTCUSDT', 'ETHUSDT', 'ZECUSDT'], 'BTCUSDT'
        self.init_databases()
        self.central_widget = QWidget();
        self.setCentralWidget(self.central_widget);
        self.layout = QVBoxLayout(self.central_widget)
        control_layout = QHBoxLayout()
        self.symbol_selector = QComboBox();
        self.symbol_selector.addItems(self.symbols);
        self.symbol_selector.currentTextChanged.connect(self.on_symbol_changed)
        self.history_button = QPushButton("История сигналов");
        self.history_button.clicked.connect(self.show_history)
        self.preview_button = QPushButton("Предпросмотр поста");
        self.preview_button.clicked.connect(self.show_telegram_preview);
        self.preview_button.setEnabled(False)
        control_layout.addWidget(QLabel("Монета:"));
        control_layout.addWidget(self.symbol_selector);
        control_layout.addStretch();
        control_layout.addWidget(self.history_button);
        control_layout.addWidget(self.preview_button)
        self.layout.addLayout(control_layout)
        self.chart_widget = CandlestickWidget()
        self.layout.addWidget(self.chart_widget)
        self.analyze_button = QPushButton("Обновить данные и получить прогноз");
        self.analyze_button.clicked.connect(self.run_analysis)
        self.layout.addWidget(self.analyze_button)
        self.load_and_display_chart()

    # ... (Остальные методы до show_telegram_preview без изменений) ...
    def init_databases(self):
        for symbol in self.symbols: db.init_db(symbol)
        db.init_signals_db()

    def on_symbol_changed(self, symbol):
        self.current_symbol = symbol;
        self.preview_button.setEnabled(False);
        self.load_and_display_chart()

    def load_and_display_chart(self):
        self.statusBar().showMessage(f"Загрузка данных для {self.current_symbol} из локальной базы...")
        chart_data = db.load_candles(self.current_symbol)
        for candle in chart_data: candle['time'] = candle.get('timestamp', 0)
        self.chart_widget.set_data(chart_data)
        if chart_data:
            self.statusBar().showMessage(f"График для {self.current_symbol} построен.", 5000)
        else:
            self.statusBar().showMessage(f"Локальных данных для {self.current_symbol} нет.", 5000)

    def update_crypto_data(self):
        last_ts = db.get_last_timestamp(self.current_symbol);
        self.statusBar().showMessage(f"Проверка новых данных для {self.current_symbol}...")
        url, params = "https://data-api.binance.vision/api/v3/klines", {'symbol': self.current_symbol, 'interval': '15m',
                                                                'limit': 1000}
        if last_ts > 0: params['startTime'] = last_ts + 1
        try:
            proxies = getproxies()
            # Локальный HTTP-прокси туннелирует HTTPS через CONNECT.
            for protocol, proxy_url in list(proxies.items()):
                parsed = urlsplit(proxy_url)
                if parsed.scheme == "https" and parsed.hostname in ("localhost", "127.0.0.1", "::1"):
                    proxies[protocol] = urlunsplit(parsed._replace(scheme="http"))
            r = requests.get(url, params=params, proxies=proxies, timeout=(8, 20));
            r.raise_for_status();
            data = r.json()
            if not data: self.statusBar().showMessage("Нет новых данных.", 3000); return True
            formatted = [{'timestamp': int(i[0]), 'open': float(i[1]), 'high': float(i[2]), 'low': float(i[3]),
                          'close': float(i[4])} for i in data]
            db.save_candles(self.current_symbol, formatted);
            self.statusBar().showMessage(f"Загружено {len(formatted)} новых свечей.", 5000)
            return True
        except requests.exceptions.RequestException as e:
            QMessageBox.critical(self, "Ошибка сети", f"Не удалось загрузить данные: {e}"); return False

    def run_analysis(self):
        if self.update_crypto_data(): self.load_and_display_chart(); self.get_gemini_forecast()

    def get_gemini_forecast(self):
        candle_data = db.load_candles(self.current_symbol, limit=50)
        if not candle_data: return
        self.analyze_button.setEnabled(False);
        self.statusBar().showMessage("Отправка запроса в Gemini AI...")
        data_string = "".join([
                                  f"Время: {datetime.fromtimestamp(c['timestamp'] / 1000).strftime('%Y-%m-%d %H:%M')}, O:{c['open']}, H:{c['high']}, L:{c['low']}, C:{c['close']}\n"
                                  for c in candle_data])
        self.thread = QThread();
        self.worker = GeminiWorker(self.current_symbol, data_string)
        self.worker.moveToThread(self.thread);
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.on_gemini_success);
        self.worker.error.connect(self.on_gemini_error)
        self.thread.start()

    def on_gemini_success(self, result):
        self.statusBar().showMessage("Прогноз получен! Можно создавать пост.", 5000)
        sl, tp1, tp2 = result['sl'], result['tp1'], result['tp2']
        db.save_signal(self.current_symbol, sl, tp1, tp2)
        all_candles = db.load_candles(self.current_symbol)
        if all_candles:
            entry_price = all_candles[-1]['close']
            self.chart_widget.set_levels(sl, tp1, tp2, entry_price)
        self.preview_button.setEnabled(True);
        self.cleanup_thread()

    def on_gemini_error(self, error_message):
        QMessageBox.warning(self, "Ошибка Gemini", error_message);
        self.cleanup_thread()

    def cleanup_thread(self):
        self.analyze_button.setEnabled(True);
        self.thread.quit();
        self.thread.wait()

    def show_history(self):
        dialog = SignalHistoryDialog(self);
        dialog.signal_selected.connect(self.on_historical_signal_selected);
        dialog.exec_()

    # <<< ИЗМЕНЕНИЕ: Возвращаем простую и надежную линейную логику >>>
    def show_telegram_preview(self):
        if not self.chart_widget.data or self.chart_widget.entry_price is None:
            QMessageBox.warning(self, "Нет данных", "Нет данных для создания поста.");
            return

        self.statusBar().showMessage("Генерация изображения для поста...")
        QApplication.processEvents()

        # --- НАЧАЛО ИЗМЕНЕНИЙ ---

        # Логика определения preview_data (остается без изменений)
        all_levels = [lvl for lvl in
                      [self.chart_widget.stop_loss, self.chart_widget.take_profit_1, self.chart_widget.take_profit_2] if
                      lvl]
        min_level, max_level = min(all_levels), max(all_levels)
        max_scan_depth, start_index = 480, len(self.chart_widget.data) - 1
        for i in range(len(self.chart_widget.data) - 192, 0, -1):
            candle = self.chart_widget.data[i]
            if candle['low'] < min_level or candle['high'] > max_level: start_index = i; break
            if (len(self.chart_widget.data) - i) > max_scan_depth: start_index = i; break
        preview_data = self.chart_widget.data[start_index:]

        # Добавляем расчет R/R, как в tg_poster
        entry = self.chart_widget.entry_price
        sl = self.chart_widget.stop_loss
        tp1 = self.chart_widget.take_profit_1
        risk = abs(entry - sl)
        reward1 = abs(tp1 - entry)
        rr_ratio_text = f"{(reward1 / risk):.2f} к 1 (до TP1)" if risk > 0 else "не определено"

        # Вызываем обновленный генератор со всеми параметрами
        try:
            chart_pixmap = post_generator.generate_post_image(
                symbol=self.current_symbol,
                data=preview_data,
                sl=sl,
                tp1=tp1,
                tp2=self.chart_widget.take_profit_2,
                entry_price=entry,
                rr_text=rr_ratio_text  # Передаем рассчитанный R/R
            )
        except RuntimeError as e:
            self.statusBar().showMessage("Не удалось создать изображение поста.", 5000)
            QMessageBox.warning(self, "Ошибка предпросмотра", str(e))
            return

        # --- КОНЕЦ ИЗМЕНЕНИЙ ---

        self.statusBar().showMessage("Изображение готово.", 3000)

        # Показываем предпросмотр (этот вызов остается без изменений)
        tg_poster.show_preview(
            parent=self, chart_image=chart_pixmap, symbol=self.current_symbol,
            last_price=self.chart_widget.entry_price, stop_loss=self.chart_widget.stop_loss,
            tp1=self.chart_widget.take_profit_1, tp2=self.chart_widget.take_profit_2
        )

    def on_historical_signal_selected(self, signal_data):
        symbol = signal_data['symbol']

        def apply_levels():
            sl, tp1 = signal_data['stop_loss'], signal_data['take_profit']
            tp2 = signal_data.get('take_profit_2', tp1)
            entry_price = self.chart_widget.data[-1]['close'] if self.chart_widget.data else None
            self.chart_widget.set_levels(sl, tp1, tp2, entry_price)
            self.preview_button.setEnabled(True)

        if self.current_symbol == symbol:
            apply_levels()
        else:
            self.symbol_selector.setCurrentText(symbol)
            QTimer.singleShot(0, apply_levels)


if __name__ == '__main__':
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
