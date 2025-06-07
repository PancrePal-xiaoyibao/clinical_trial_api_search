#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
临床试验翻译模块
支持多种国产LLM模型的医学文本翻译
作者: 小胰宝团队
"""

import json
import os
import hashlib
import time
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import requests

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('translation.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class TranslationResult:
    """翻译结果数据类"""
    original: str
    translated: str
    cached: bool = False
    provider: str = ""
    model: str = ""
    timestamp: float = 0.0

class LLMTranslator:
    """LLM翻译器基类"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.api_key = config.get('api_key', '')
        self.base_url = config.get('base_url', '')
        self.model = config.get('model', '')
        self.temperature = config.get('temperature', 0.3)
        self.max_tokens = config.get('max_tokens', 2000)
        self.timeout = config.get('timeout', 30)
        
    def translate(self, text: str, system_prompt: str) -> str:
        """翻译文本 - 子类需要实现"""
        raise NotImplementedError

class ZhipuTranslator(LLMTranslator):
    """智谱AI翻译器"""
    
    def translate(self, text: str, system_prompt: str) -> str:
        """使用智谱AI进行翻译"""
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        data = {
            'model': self.model,
            'messages': [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': f'请翻译以下内容：\n{text}'}
            ],
            'temperature': self.temperature,
            'max_tokens': self.max_tokens
        }
        
        try:
            response = requests.post(
                f'{self.base_url}/chat/completions',
                headers=headers,
                json=data,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            result = response.json()
            return result['choices'][0]['message']['content'].strip()
            
        except Exception as e:
            logger.error(f"智谱AI翻译失败: {e}")
            raise

class QwenTranslator(LLMTranslator):
    """通义千问翻译器"""
    
    def translate(self, text: str, system_prompt: str) -> str:
        """使用通义千问进行翻译"""
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        data = {
            'model': self.model,
            'input': {
                'messages': [
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': f'请翻译以下内容：\n{text}'}
                ]
            },
            'parameters': {
                'temperature': self.temperature,
                'max_tokens': self.max_tokens
            }
        }
        
        try:
            response = requests.post(
                f'{self.base_url}/chat/completions',
                headers=headers,
                json=data,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            result = response.json()
            return result['output']['choices'][0]['message']['content'].strip()
            
        except Exception as e:
            logger.error(f"通义千问翻译失败: {e}")
            raise

class DeepSeekTranslator(LLMTranslator):
    """DeepSeek翻译器"""
    
    def translate(self, text: str, system_prompt: str) -> str:
        """使用DeepSeek进行翻译"""
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        data = {
            'model': self.model,
            'messages': [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': f'请翻译以下内容：\n{text}'}
            ],
            'temperature': self.temperature,
            'max_tokens': self.max_tokens,
            'stream': False
        }
        
        try:
            response = requests.post(
                f'{self.base_url}/chat/completions',
                headers=headers,
                json=data,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            result = response.json()
            return result['choices'][0]['message']['content'].strip()
            
        except Exception as e:
            logger.error(f"DeepSeek翻译失败: {e}")
            raise

class TranslationCache:
    """翻译缓存管理器"""
    
    def __init__(self, cache_file: str):
        self.cache_file = cache_file
        self.cache = self._load_cache()
        
    def _load_cache(self) -> Dict[str, Dict]:
        """加载缓存文件"""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"加载缓存文件失败: {e}")
        return {}
    
    def _save_cache(self):
        """保存缓存到文件"""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存缓存文件失败: {e}")
    
    def _get_cache_key(self, text: str) -> str:
        """生成缓存键"""
        return hashlib.md5(text.encode('utf-8')).hexdigest()
    
    def get(self, text: str) -> Optional[str]:
        """从缓存获取翻译"""
        key = self._get_cache_key(text)
        cache_entry = self.cache.get(key)
        if cache_entry:
            logger.info(f"缓存命中: {text[:50]}...")
            return cache_entry.get('translated')
        return None
    
    def set(self, text: str, translated: str, provider: str, model: str):
        """设置缓存"""
        key = self._get_cache_key(text)
        self.cache[key] = {
            'original': text,
            'translated': translated,
            'provider': provider,
            'model': model,
            'timestamp': time.time()
        }
        self._save_cache()
        logger.info(f"缓存已保存: {text[:50]}...")

class MedicalTranslator:
    """医学翻译主类"""
    
    def __init__(self, config_file: str = 'config.json'):
        self.config = self._load_config(config_file)
        self.llm_config = self.config['llm']
        self.translation_config = self.config['translation']
        self.system_prompt = self.config.get('system_prompt', '')
        
        # 初始化翻译器
        self.translator = self._create_translator()
        
        # 初始化缓存
        if self.translation_config.get('cache_enabled', True):
            cache_file = self.translation_config.get('cache_file', 'translation_cache.json')
            self.cache = TranslationCache(cache_file)
        else:
            self.cache = None
            
        logger.info(f"医学翻译器初始化完成 - 提供商: {self.llm_config['provider']}, 模型: {self.llm_config['model']}")
    
    def _load_config(self, config_file: str) -> Dict[str, Any]:
        """加载配置文件"""
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            raise
    
    def _create_translator(self) -> LLMTranslator:
        """创建翻译器实例"""
        provider = self.llm_config['provider'].lower()
        
        if provider == 'zhipu':
            return ZhipuTranslator(self.llm_config)
        elif provider == 'qwen':
            return QwenTranslator(self.llm_config)
        elif provider == 'deepseek':
            return DeepSeekTranslator(self.llm_config)
        else:
            raise ValueError(f"不支持的LLM提供商: {provider}")
    
    def translate_text(self, text: str) -> TranslationResult:
        """翻译单个文本"""
        if not text or not text.strip():
            return TranslationResult(original=text, translated=text)
        
        # 检查缓存
        if self.cache:
            cached_translation = self.cache.get(text)
            if cached_translation:
                return TranslationResult(
                    original=text,
                    translated=cached_translation,
                    cached=True,
                    provider=self.llm_config['provider'],
                    model=self.llm_config['model'],
                    timestamp=time.time()
                )
        
        # 执行翻译
        try:
            translated = self.translator.translate(text, self.system_prompt)
            
            # 保存到缓存
            if self.cache:
                self.cache.set(
                    text, translated, 
                    self.llm_config['provider'], 
                    self.llm_config['model']
                )
            
            return TranslationResult(
                original=text,
                translated=translated,
                cached=False,
                provider=self.llm_config['provider'],
                model=self.llm_config['model'],
                timestamp=time.time()
            )
            
        except Exception as e:
            logger.error(f"翻译失败: {e}")
            # 翻译失败时返回原文
            return TranslationResult(
                original=text,
                translated=text,
                cached=False,
                provider=self.llm_config['provider'],
                model=self.llm_config['model'],
                timestamp=time.time()
            )
    
    def translate_batch(self, texts: List[str]) -> List[TranslationResult]:
        """批量翻译"""
        results = []
        batch_size = self.translation_config.get('batch_size', 5)
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            logger.info(f"翻译批次 {i//batch_size + 1}: {len(batch)} 个文本")
            
            for text in batch:
                result = self.translate_text(text)
                results.append(result)
                
                # 避免API限流
                if not result.cached:
                    time.sleep(0.5)
        
        return results
    
    def is_enabled(self) -> bool:
        """检查翻译功能是否启用"""
        return self.translation_config.get('enabled', True)
    
    def get_translatable_fields(self) -> List[str]:
        """获取需要翻译的字段列表"""
        return self.translation_config.get('fields_to_translate', [])
    
    def translate(self, text: str) -> str:
        """简化的翻译方法，返回翻译后的文本"""
        if not self.is_enabled():
            return text
        
        result = self.translate_text(text)
        return result.translated

if __name__ == '__main__':
    # 测试翻译功能
    translator = MedicalTranslator()
    
    test_texts = [
        "Pancreatic Adenocarcinoma Metastatic",
        "BRCA1 Mutation",
        "Inclusion Criteria: Age ≥ 18 years, confirmed pancreatic cancer"
    ]
    
    for text in test_texts:
        result = translator.translate_text(text)
        print(f"原文: {result.original}")
        print(f"译文: {result.translated}")
        print(f"缓存: {result.cached}")
        print("-" * 50)