import os
from PyQt5.QtWidgets import QFileDialog, QMessageBox

def convert_using_table(viewer):
    file_path, _ = QFileDialog.getOpenFileName(viewer, viewer.tr("select_conversion_table"), "", "文本文件 (*.txt)")
    if file_path:
        try:
            gxt_file_path = viewer.gxt_file_path or viewer.gxt_path_entry.text()
            if not gxt_file_path:
                gxt_file_path, _ = QFileDialog.getOpenFileName(viewer, viewer.tr("select_gxt_file"), "", "GXT文件 (*.gxt)")
                if not gxt_file_path:
                    raise FileNotFoundError(viewer.tr("error_no_gxt_path_provided"))

            gxt_txt_path = os.path.splitext(gxt_file_path)[0] + '.txt'

            with open(gxt_txt_path, 'r', encoding='utf-8') as gxt_txt_file:
                converted_lines = gxt_txt_file.readlines()

            with open(file_path, 'r', encoding='utf-8') as table_file:
                hex_table = table_file.readlines()

            conversion_dict = {}
            for line in hex_table:
                line = line.strip().split('\t')
                if len(line) == 2:
                    conversion_dict[line[1]] = line[0]

            updated_lines = []
            for line in converted_lines:
                if '=' in line:
                    key, value = line.split('=', 1)
                    converted_value = "".join(
                        conversion_dict.get(f"{ord(char):04x}", char) if ord(char) > 127 else char 
                        for char in value
                    )
                    updated_lines.append(f"{key}={converted_value}")
                else:
                    updated_lines.append(line)

            with open(gxt_txt_path, 'w', encoding='utf-8') as output_file:
                output_file.writelines(updated_lines)

            viewer.display_gxt_content_in_table(''.join(updated_lines))

            QMessageBox.information(viewer, viewer.tr("提示"), viewer.tr("info_conversion_complete", gxt_txt_path=gxt_txt_path))
        except Exception as e:
            QMessageBox.critical(viewer, viewer.tr("错误"), viewer.tr("error_conversion", error=str(e)))
    else:
        QMessageBox.warning(viewer, viewer.tr("警告"), viewer.tr("warning_no_conversion_table_selected"))
