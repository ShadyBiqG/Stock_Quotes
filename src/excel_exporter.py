"""
Экспорт результатов анализа в Excel с форматированием
"""

import logging
from typing import List, Dict
from datetime import date
from pathlib import Path
import os
import tempfile
import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

logger = logging.getLogger(__name__)


class ExcelExporter:
    """Класс для экспорта результатов в Excel"""
    
    # Цветовая схема
    COLORS = {
        'РАСТЕТ': 'C6EFCE',      # Зеленый
        'ПАДАЕТ': 'FFC7CE',      # Красный
        'СТАБИЛЬНА': 'FFEB9C',   # Желтый
        'ОШИБКА': 'FFC7CE',      # Красный
        'ПОДОЗРИТЕЛЬНО': 'FFD9B3', # Оранжевый
        'HEADER': '4472C4'       # Синий
    }
    
    def __init__(self, output_dir: str = "output/exports"):
        """
        Инициализация экспортера
        
        Args:
            output_dir: Директория для сохранения файлов
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Экспортер инициализирован: {self.output_dir}")
    
    def export(self, results: List[Dict], 
               analysis_date: date = None,
               filename: str = None) -> Path:
        """
        Экспорт результатов в Excel
        
        Args:
            results: Результаты анализа
            analysis_date: Дата анализа
            filename: Имя файла (если None - генерируется автоматически)
            
        Returns:
            Путь к созданному файлу
        """
        if analysis_date is None:
            analysis_date = date.today()
        
        if filename is None:
            filename = f"{analysis_date}_analysis.xlsx"
        
        filepath = self.output_dir / filename
        
        logger.info(f"Экспорт результатов в {filepath}")

        return self._export_with_safe_replace(filepath, results)

    def _export_with_safe_replace(self, target_path: Path, results: List[Dict]) -> Path:
        """
        Экспорт в Excel с защитой от блокировки файла на Windows.
        Пишем во временный файл и затем заменяем целевой. Если целевой файл открыт,
        подбираем новое имя вида *_1.xlsx, *_2.xlsx.

        Args:
            target_path: Желаемый путь итогового файла
            results: Результаты анализа

        Returns:
            Фактический путь созданного файла
        """
        self.output_dir.mkdir(parents=True, exist_ok=True)

        attempts = 10
        last_error = None

        for i in range(attempts):
            final_path = target_path if i == 0 else self._with_suffix_counter(target_path, i)

            tmp_path = None
            try:
                fd, tmp_name = tempfile.mkstemp(
                    suffix=final_path.suffix,
                    prefix=f".tmp_{final_path.stem}_",
                    dir=str(final_path.parent)
                )
                os.close(fd)
                tmp_path = Path(tmp_name)

                # Создание Excel файла во временный путь
                with pd.ExcelWriter(tmp_path, engine='openpyxl') as writer:
                    self._create_summary_sheet(results, writer)
                    self._create_details_sheet(results, writer)
                    self._create_quality_sheet(results, writer)

                # Применение форматирования
                self._apply_formatting(tmp_path)

                # Атомарная замена (или создание, если файла нет)
                os.replace(tmp_path, final_path)

                logger.info(f"Файл создан: {final_path}")
                return final_path

            except PermissionError as e:
                last_error = e
                logger.warning(f"Нет доступа к файлу {final_path} (возможно открыт в Excel). Попытка {i + 1}/{attempts}")

                if tmp_path and tmp_path.exists():
                    try:
                        tmp_path.unlink()
                    except OSError:
                        pass

                continue

            except Exception:
                if tmp_path and tmp_path.exists():
                    try:
                        tmp_path.unlink()
                    except OSError:
                        pass
                raise

        raise PermissionError(
            f"Не удалось сохранить Excel файл. Проверьте, что файл не открыт и доступна запись: {target_path}"
        ) from last_error

    def _with_suffix_counter(self, path: Path, counter: int) -> Path:
        """
        Построить путь с числовым суффиксом: file.xlsx -> file_1.xlsx

        Args:
            path: Исходный путь
            counter: Номер суффикса

        Returns:
            Новый путь
        """
        return path.with_name(f"{path.stem}_{counter}{path.suffix}")
    
    def _create_summary_sheet(self, results: List[Dict], writer) -> None:
        """
        Создать лист "Сводка"
        
        Args:
            results: Результаты анализа
            writer: Excel writer
        """
        # Группировка по тикерам
        summary_data = {}
        
        for r in results:
            ticker = r['ticker']
            
            if ticker not in summary_data:
                summary_data[ticker] = {
                    'Тикер': ticker,
                    'Компания': r.get('name', ''),
                    'Описание': r.get('description', ''),
                    'Сектор': r.get('sector', ''),
                    'Цена': r['price'],
                    'Изм.%': r['change'],
                    'Объем': r['volume']
                }
            
            # Прогнозы моделей
            model_name = r['model_name']
            summary_data[ticker][model_name] = r['prediction']
        
        # Создание DataFrame
        df = pd.DataFrame(list(summary_data.values()))
        
        # Вычисление консенсуса
        model_columns = [col for col in df.columns if col not in [
            'Тикер', 'Компания', 'Описание', 'Сектор', 'Цена', 'Изм.%', 'Объем'
        ]]
        
        def calculate_consensus(row):
            predictions = [row[col] for col in model_columns if pd.notna(row[col])]
            if not predictions:
                return 'Н/Д'
            
            # Если все согласны
            if len(set(predictions)) == 1:
                return predictions[0]
            
            # Большинство
            from collections import Counter
            counts = Counter(predictions)
            most_common = counts.most_common(1)[0]
            
            if most_common[1] > len(predictions) / 2:
                return f"{most_common[0]} ({most_common[1]}/{len(predictions)})"
            
            return f"Разногласие ({most_common[1]}/{len(predictions)})"
        
        df['Консенсус'] = df.apply(calculate_consensus, axis=1)
        
        # Сохранение в Excel
        df.to_excel(writer, sheet_name='Сводка', index=False)
        
        logger.debug("Создан лист 'Сводка'")
    
    def _create_details_sheet(self, results: List[Dict], writer) -> None:
        """
        Создать лист "Детали"
        
        Args:
            results: Результаты анализа
            writer: Excel writer
        """
        details_data = []
        
        for r in results:
            # Полный текст анализа
            analysis_text = r.get('analysis_text', '')
            
            # Ключевые факторы
            key_factors = r.get('key_factors', [])
            if key_factors:
                factors_text = '\n'.join([
                    f"{i+1}. {factor}" 
                    for i, factor in enumerate(key_factors)
                ])
            else:
                # Fallback на старое поле reasons для обратной совместимости
                reasons = r.get('reasons', [])
                factors_text = '\n'.join([
                    f"{i+1}. {reason}" 
                    for i, reason in enumerate(reasons)
                ]) if reasons else 'Не указаны'
            
            details_data.append({
                'Тикер': r['ticker'],
                'Компания': r.get('name', ''),
                'Цена': r['price'],
                'Изм.%': r['change'],
                'Модель': r['model_name'],
                'Прогноз': r['prediction'],
                'Анализ': analysis_text if analysis_text else 'Не предоставлен',
                'Ключевые факторы': factors_text,
                'Уверенность': r['confidence'],
                'Токенов': r.get('tokens_used', 0)
            })
        
        df = pd.DataFrame(details_data)
        df.to_excel(writer, sheet_name='Детали', index=False)
        
        logger.debug("Создан лист 'Детали'")
    
    def _create_quality_sheet(self, results: List[Dict], writer) -> None:
        """
        Создать лист "Анализ качества"
        
        Args:
            results: Результаты анализа
            writer: Excel writer
        """
        # Группировка по тикерам
        stocks = {}
        for r in results:
            ticker = r['ticker']
            if ticker not in stocks:
                stocks[ticker] = []
            stocks[ticker].append(r)
        
        quality_data = []
        
        for ticker, stock_results in stocks.items():
            predictions = [r['prediction'] for r in stock_results]
            
            # Консенсус
            has_consensus = len(set(predictions)) == 1
            
            # Подозрительные ответы
            suspicious_count = sum(
                1 for r in stock_results
                if r.get('validation_flags', {}).get('trust_level') == 'LOW'
            )
            
            # Средняя уверенность
            confidences = [r['confidence'] for r in stock_results]
            conf_map = {'ВЫСОКАЯ': 3, 'СРЕДНЯЯ': 2, 'НИЗКАЯ': 1}
            
            if confidences:
                avg_conf = sum(conf_map.get(c, 1) for c in confidences) / len(confidences)
                avg_conf_text = 'ВЫСОКАЯ' if avg_conf >= 2.5 else (
                    'СРЕДНЯЯ' if avg_conf >= 1.5 else 'НИЗКАЯ'
                )
            else:
                avg_conf_text = 'Н/Д'
            
            quality_data.append({
                'Тикер': ticker,
                'Консенсус': 'Да' if has_consensus else 'Нет',
                'Разных мнений': len(set(predictions)),
                'Подозрительных': suspicious_count,
                'Средняя уверенность': avg_conf_text,
                'Всего токенов': sum(r.get('tokens_used', 0) for r in stock_results)
            })
        
        # Проверка наличия данных
        if not quality_data:
            # Если нет данных, создаем пустой лист с сообщением
            df = pd.DataFrame([{
                'Тикер': 'Нет данных',
                'Консенсус': '-',
                'Разных мнений': '-',
                'Подозрительных': '-',
                'Средняя уверенность': '-',
                'Всего токенов': '-'
            }])
            df.to_excel(writer, sheet_name='Анализ качества', index=False)
            logger.warning("Нет данных для анализа качества")
            return
        
        df = pd.DataFrame(quality_data)
        
        # Итоговая статистика (только если есть данные)
        total_consensus = sum(1 for d in quality_data if d['Консенсус'] == 'Да')
        total_count = len(quality_data)
        avg_opinions = sum(d['Разных мнений'] for d in quality_data) / total_count
        total_suspicious = sum(d['Подозрительных'] for d in quality_data)
        total_tokens = sum(d['Всего токенов'] for d in quality_data)
        
        total_stats = pd.DataFrame([{
            'Тикер': 'ИТОГО',
            'Консенсус': f"{total_consensus} / {total_count}",
            'Разных мнений': f"{avg_opinions:.1f}",
            'Подозрительных': total_suspicious,
            'Средняя уверенность': '-',
            'Всего токенов': total_tokens
        }])
        
        df = pd.concat([df, total_stats], ignore_index=True)
        df.to_excel(writer, sheet_name='Анализ качества', index=False)
        
        logger.debug("Создан лист 'Анализ качества'")
    
    def _apply_formatting(self, filepath: Path) -> None:
        """
        Применить форматирование к Excel файлу
        
        Args:
            filepath: Путь к файлу
        """
        wb = load_workbook(filepath)
        
        # Форматирование листа "Сводка"
        if 'Сводка' in wb.sheetnames:
            self._format_summary_sheet(wb['Сводка'])
        
        # Форматирование листа "Детали"
        if 'Детали' in wb.sheetnames:
            self._format_details_sheet(wb['Детали'])
        
        # Форматирование листа "Анализ качества"
        if 'Анализ качества' in wb.sheetnames:
            self._format_quality_sheet(wb['Анализ качества'])
        
        wb.save(filepath)
        logger.debug("Применено форматирование")
    
    def _format_summary_sheet(self, ws) -> None:
        """Форматирование листа Сводка"""
        # Заголовки
        header_fill = PatternFill(start_color=self.COLORS['HEADER'], 
                                  end_color=self.COLORS['HEADER'],
                                  fill_type='solid')
        header_font = Font(bold=True, color='FFFFFF')
        
        for cell in ws[1]:
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal='center', vertical='center')
        
        # Цветовое кодирование прогнозов
        for row in ws.iter_rows(min_row=2):
            for cell in row:
                if cell.value in self.COLORS:
                    cell.fill = PatternFill(
                        start_color=self.COLORS[cell.value],
                        end_color=self.COLORS[cell.value],
                        fill_type='solid'
                    )
                
                # Выравнивание
                if cell.column <= 4:  # Текстовые колонки
                    cell.alignment = Alignment(horizontal='left', 
                                              vertical='top',
                                              wrap_text=True)
                else:
                    cell.alignment = Alignment(horizontal='center',
                                              vertical='center')
        
        # Автоширина колонок
        for column in ws.columns:
            max_length = 0
            column_letter = get_column_letter(column[0].column)
            
            for cell in column:
                try:
                    if cell.value:
                        max_length = max(max_length, len(str(cell.value)))
                except:
                    pass
            
            adjusted_width = min(max_length + 2, 50)
            ws.column_dimensions[column_letter].width = adjusted_width
        
        # Фиксация заголовка
        ws.freeze_panes = 'A2'
    
    def _format_details_sheet(self, ws) -> None:
        """Форматирование листа Детали"""
        # Заголовки
        header_fill = PatternFill(start_color=self.COLORS['HEADER'],
                                  end_color=self.COLORS['HEADER'],
                                  fill_type='solid')
        header_font = Font(bold=True, color='FFFFFF')
        
        for cell in ws[1]:
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal='center', vertical='center')
        
        # Найти индексы колонок для текстовых полей
        header_row = [cell.value for cell in ws[1]]
        analysis_col = header_row.index('Анализ') + 1 if 'Анализ' in header_row else None
        factors_col = header_row.index('Ключевые факторы') + 1 if 'Ключевые факторы' in header_row else None
        
        # Перенос текста в анализе и факторах
        for row in ws.iter_rows(min_row=2):
            for cell in row:
                # Колонка "Анализ"
                if analysis_col and cell.column == analysis_col:
                    cell.alignment = Alignment(wrap_text=True,
                                              vertical='top',
                                              horizontal='left')
                    ws.row_dimensions[cell.row].height = 80
                
                # Колонка "Ключевые факторы"
                elif factors_col and cell.column == factors_col:
                    cell.alignment = Alignment(wrap_text=True,
                                              vertical='top',
                                              horizontal='left')
                    ws.row_dimensions[cell.row].height = 80
                
                # Остальные колонки
                else:
                    cell.alignment = Alignment(vertical='center',
                                              horizontal='center')
        
        # Установка ширины колонок
        for i, column in enumerate(ws.columns, 1):
            column_letter = get_column_letter(i)
            
            # Широкие колонки для текстовых полей
            if i == analysis_col:
                ws.column_dimensions[column_letter].width = 70
            elif i == factors_col:
                ws.column_dimensions[column_letter].width = 50
            else:
                # Автоширина для остальных колонок
                max_length = 0
                for cell in column:
                    try:
                        if cell.value:
                            max_length = max(max_length, len(str(cell.value)))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 25)
                ws.column_dimensions[column_letter].width = adjusted_width
        
        # Фиксация заголовка
        ws.freeze_panes = 'A2'
    
    def _format_quality_sheet(self, ws) -> None:
        """Форматирование листа Анализ качества"""
        # Заголовки
        header_fill = PatternFill(start_color=self.COLORS['HEADER'],
                                  end_color=self.COLORS['HEADER'],
                                  fill_type='solid')
        header_font = Font(bold=True, color='FFFFFF')
        
        for cell in ws[1]:
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal='center')
        
        # Выделение итоговой строки
        last_row = ws.max_row
        for cell in ws[last_row]:
            cell.font = Font(bold=True)
            cell.fill = PatternFill(start_color='E7E6E6',
                                   end_color='E7E6E6',
                                   fill_type='solid')
        
        # Автоширина
        for column in ws.columns:
            max_length = 0
            column_letter = get_column_letter(column[0].column)
            
            for cell in column:
                try:
                    if cell.value:
                        max_length = max(max_length, len(str(cell.value)))
                except:
                    pass
            
            adjusted_width = min(max_length + 2, 30)
            ws.column_dimensions[column_letter].width = adjusted_width


# Пример использования
if __name__ == "__main__":
    from .database import Database
    
    logging.basicConfig(level=logging.INFO)
    
    # Получение результатов из БД
    with Database() as db:
        results = db.get_analysis_results()
    
    # Экспорт
    exporter = ExcelExporter()
    filepath = exporter.export(results)
    
    print(f"✅ Файл создан: {filepath}")
