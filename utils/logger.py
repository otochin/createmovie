"""
ログ管理モジュール
"""
import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

from config.config import config


def setup_logger(
    name: str,
    log_file: Optional[Path] = None,
    level: Optional[str] = None,
    format_string: Optional[str] = None
) -> logging.Logger:
    """
    ロガーを設定して返す
    
    Args:
        name: ロガー名
        log_file: ログファイルのパス（Noneの場合はファイル出力なし）
        level: ログレベル（Noneの場合はconfigから読み込む）
        format_string: ログフォーマット（Noneの場合はデフォルト）
    
    Returns:
        logging.Logger: 設定済みのロガー
    """
    logger = logging.getLogger(name)
    
    # 既に設定済みの場合はそのまま返す
    if logger.handlers:
        return logger
    
    # ログレベルの設定
    log_level = level or config.log_level
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    
    # フォーマットの設定
    if format_string is None:
        format_string = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    formatter = logging.Formatter(format_string, datefmt="%Y-%m-%d %H:%M:%S")
    
    # コンソールハンドラの設定
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # ファイルハンドラの設定（log_fileが指定されている場合）
    if log_file:
        # ログディレクトリを作成
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def get_logger(name: str = __name__) -> logging.Logger:
    """
    ロガーを取得（簡易版）
    
    Args:
        name: ロガー名（デフォルトは呼び出し元のモジュール名）
    
    Returns:
        logging.Logger: ロガー
    """
    logger = logging.getLogger(name)
    
    # まだ設定されていない場合は設定する
    if not logger.handlers:
        log_file = config.log_dir / f"{name}.log"
        return setup_logger(name, log_file=log_file)
    
    return logger


# デフォルトロガー
default_logger = get_logger("createmovie")
