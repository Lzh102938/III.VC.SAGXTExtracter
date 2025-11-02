import os
import sys
import asyncio
import aiohttp
import time
import logging
from PyQt6.QtWidgets import QFileDialog, QMessageBox, QApplication
from asyncio import Semaphore

# 配置参数
API_URL = "https://api.deepseek.com/v1/chat/completions"  # DeepSeek API的请求地址
BATCH_SIZE = 20  # 每批次翻译的文本行数
MAX_CONCURRENT_REQUESTS = 50  # 最大并发请求数
MAX_RETRIES = 3  # 请求失败时的最大重试次数
REQUEST_TIMEOUT = 120  # 请求超时时间（秒）


def setup_logger():
    logger = logging.getLogger("Translator")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%H:%M:%S')
        console_handler.setFormatter(console_format)
        logger.addHandler(console_handler)
    return logger

logger = setup_logger()

def get_table_lines(viewer):
    """从表格获取所有可翻译的行，返回[(row, key, value)]"""
    logger.info("开始获取表格行数据")
    lines = []
    for row in range(viewer.output_table.rowCount()):
        key_item = viewer.output_table.item(row, 0)
        value_item = viewer.output_table.item(row, 1)
        if key_item and value_item:
            key = key_item.text()
            value = value_item.text()
            if key and value and not (key.startswith('[') and key.endswith(']')):
                lines.append((row, key, value))
    logger.info(f"总共获取到 {len(lines)} 行可翻译数据")
    return lines

async def translate_batch(self, batch, api_key, semaphore):
    """异步翻译一批文本"""
    async with semaphore:  # 限制并发数量
        logger.info(f"开始翻译批次，包含 {len(batch)} 行")
        batch_contents = "\n".join([f"{i+1}. {item[2]}" for i, item in enumerate(batch)])
        data = {
            "model": "deepseek-chat",
            "messages": [
                {
                    "role": "system",
                    "content": self.tr("translate_prompt")
                },
                {
                    "role": "user",
                    "content": self.tr("translate_batch_prompt", contents=batch_contents)
                }
            ],
            "temperature": 0.1,
            "stream": False
        }
        # 仅在日志中隐藏部分API密钥，实际请求中使用完整密钥
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        log_headers = {
            "Authorization": f"Bearer {api_key[:3]}{'*' * (len(api_key) - 6)}{api_key[-3:]}" if api_key else "",
            "Content-Type": "application/json"
        }
        logger.info(f"请求头(隐藏密钥): {log_headers}")
        async with aiohttp.ClientSession(headers=headers, timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)) as session:
            for retry in range(MAX_RETRIES + 1):
                try:
                    logger.info(f"发送API请求，重试次数: {retry}")
                    async with session.post(API_URL, json=data) as resp:
                        if resp.status != 200:
                            error_text = await resp.text()
                            # 在错误信息中隐藏API密钥
                            masked_error_text = error_text.replace(api_key, f"{api_key[:3]}{'*' * (len(api_key) - 6)}{api_key[-3:]}") if api_key else error_text
                            logger.error(f"API错误: {resp.status} {masked_error_text}")
                            # 如果是认证错误，直接抛出异常，不需要重试
                            if resp.status == 401:
                                raise Exception(self.tr("error_invalid_api_key"))
                            raise Exception(f"API错误: {resp.status} {masked_error_text}")
                        resp_json = await resp.json()
                        result_text = resp_json["choices"][0]["message"]["content"].strip()
                        logger.info(f"API响应成功，结果长度: {len(result_text)} 字符，内容预览: {result_text[:10]}")
                        translations = []
                        for line in result_text.split('\n'):
                            if '.' in line:
                                line = line.split('.', 1)[1].strip()
                            translations.append(line)
                        if len(translations) != len(batch):
                            translations = result_text.split('\n')
                        if len(translations) != len(batch):
                            logger.error(f"翻译结果数量不匹配: 期望 {len(batch)}, 实际 {len(translations)}")
                            raise Exception(self.tr("error_result_count_mismatch"))
                        logger.info(f"批次翻译完成，返回 {len(translations)} 条翻译结果")
                        return translations
                except Exception as e:
                    # 在异常信息中隐藏API密钥
                    masked_error_msg = str(e).replace(api_key, f"{api_key[:3]}{'*' * (len(api_key) - 6)}{api_key[-3:]}") if api_key else str(e)
                    logger.warning(f"批次翻译失败({retry+1}/{MAX_RETRIES+1}): {masked_error_msg}")
                    if retry == MAX_RETRIES or ("invalid_api_key" in str(e)):
                        logger.error(f"批次翻译最终失败: {masked_error_msg}")
                        raise
                    await asyncio.sleep(2 ** retry)
            # 最终失败
            logger.warning("达到最大重试次数，返回原始文本")
            return [item[2] for item in batch]

async def translate_all(self, lines, progress_callback=None, api_key=None):
    """批量翻译所有行，自动更新表格，支持进度回调"""
    logger.info(f"开始翻译全部 {len(lines)} 行数据")
    total = len(lines)
    new_values = {}
    
    if total == 0:
        logger.warning("没有需要翻译的行")
        if progress_callback:
            progress_callback(0, 0, self.tr("info_no_translatable_content"))
        return
    
    # 创建信号量以限制并发请求数
    semaphore = Semaphore(MAX_CONCURRENT_REQUESTS)
    
    # 将所有批次分组
    batches = [lines[i:i+BATCH_SIZE] for i in range(0, total, BATCH_SIZE)]
    total_batches = len(batches)
    completed_batches = 0
    lock = asyncio.Lock()  # 用于保护共享变量
    
    async def translate_batch_with_progress(batch):
        nonlocal completed_batches
        for retry in range(MAX_RETRIES + 1):
            try:
                # 执行翻译
                translations = await translate_batch(self, batch, api_key, semaphore)
                
                # 更新结果和进度
                async with lock:
                    # 保存翻译结果
                    for idx, (row, key, _) in enumerate(batch):
                        new_values[row] = translations[idx]
                    
                    # 更新完成批次计数
                    completed_batches += 1
                    # 修复：正确计算已处理的行数
                    processed = sum(len(b) for b in batches[:completed_batches])
                    
                    # 更新进度
                    logger.info(f"已完成 {completed_batches}/{total_batches} 个批次翻译")
                    if progress_callback:
                        msg = f"已翻译 {processed}/{total} 行"
                        progress_callback(processed, total, msg)
                    QApplication.processEvents()
                
                return translations
            except Exception as e:
                logger.error(f"批次翻译失败 (重试 {retry + 1}/{MAX_RETRIES+1}): {e}")
                # 如果是API密钥无效错误，直接终止所有翻译任务
                if "invalid_api_key" in str(e):
                    logger.warning("检测到API密钥无效，终止所有翻译任务")
                    if progress_callback:
                        progress_callback(0, total, self.tr("error_invalid_api_key"))
                    raise
                if retry == MAX_RETRIES:
                    logger.warning(f"批次翻译最终失败，跳过该批次")
                    break
                await asyncio.sleep(2 ** retry)
        
        # 返回原始文本
        return [item[2] for item in batch]
    
    # 创建所有翻译任务
    tasks = [translate_batch_with_progress(batch) for batch in batches]
    
    # 并发执行所有翻译任务
    try:
        await asyncio.gather(*tasks, return_exceptions=True)
    except asyncio.CancelledError:
        logger.warning("翻译任务被取消，保留已翻译内容")
    except Exception as e:
        logger.error(f"翻译过程中发生错误: {e}")
        if "invalid_api_key" in str(e):
            if progress_callback:
                progress_callback(0, total, self.tr("error_invalid_api_key"))
            else:
                QMessageBox.warning(self, self.tr("error_title"), self.tr("error_invalid_api_key"))
            return
        if progress_callback:
            progress_callback(completed_batches * BATCH_SIZE, total, f"翻译出错: {str(e)}")
    
    # 更新表格
    logger.info("开始更新表格内容")
    try:
        for row, key, _ in lines:
            if row in new_values:
                self.output_table.item(row, 1).setText(new_values[row])
        logger.info("表格内容更新完成")
    except Exception as e:
        logger.error(f"更新表格时发生错误: {e}")
        raise
            
    # 更新表格
    logger.info("开始更新表格内容")
    try:
        for row, key, _ in lines:
            self.output_table.item(row, 1).setText(new_values[row])
        logger.info("表格内容更新完成")
    except Exception as e:
        logger.error(f"更新表格时发生错误: {e}")
        raise
        
    if progress_callback:
        progress_callback(total, total, self.tr("progress_translation_complete"))
    else:
        QMessageBox.information(self, self.tr("progress_translation_complete"), self.tr("info_translation_complete", count=total))
    logger.info("全部翻译任务完成")

def smart_translate(self, progress_callback=None, key=None):
    """主入口：智能翻译当前表格内容，支持进度回调。所有操作异步，主线程仅负责UI反馈。"""
    logger.info("开始智能翻译任务")
    if not key:
        logger.warning("未提供API密钥")
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.warning(self, self.tr("warning_title"), self.tr("warning_input_valid_key"))
        return
        
    lines = get_table_lines(self)
    logger.info(f"获取到 {len(lines)} 行待翻译内容")
    if not lines:
        logger.warning("没有可翻译的内容")
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.warning(self, self.tr("warning_title"), self.tr("info_no_translatable_content"))
        return
    import threading

    def run_async_translate():
        logger.info("启动异步翻译线程")
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            if progress_callback:
                try:
                    logger.info("开始带进度回调的翻译任务")
                    loop.run_until_complete(translate_all(self, lines, progress_callback=progress_callback, api_key=key))
                except Exception as e:
                    logger.error(f"带进度回调的翻译任务被中断: {e}")
                    import logging
                    logging.getLogger("Translator").warning(f"翻译被中断: {e}")
                    raise
            else:
                logger.info("开始无进度回调的翻译任务")
                loop.run_until_complete(translate_all(self, lines, api_key=key))
        except Exception as e:
            logger.error(f"翻译任务执行过程中发生异常: {e}")
        finally:
            logger.info("关闭异步事件循环")
            loop.close()
        logger.info("异步翻译线程结束")

    t = threading.Thread(target=run_async_translate)
    t.start()
    logger.info("异步翻译线程已启动")