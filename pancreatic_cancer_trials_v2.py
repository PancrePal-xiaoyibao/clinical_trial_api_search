#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
胰腺癌临床试验查询脚本 - 使用新版API v2
基于ClinicalTrials.gov API v2查找最近30天内新增或更新的活跃胰腺癌临床试验
"""

import requests
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import time
import os
from generate_report import generate_report
from translator import MedicalTranslator

class PancreaticCancerTrialsFinder:
    """胰腺癌临床试验查找器"""
    
    def __init__(self):
        # 使用新版API v2 beta端点 - 严格按照用户提供的curl示例
        self.base_url = "https://beta-ut.clinicaltrials.gov/api/v2/studies"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'PancreaticCancerTrialsFinder/1.0'
        })
        
        # 设置日志
        self.setup_logging()
        
        # 初始化翻译器（用于中文查询词转换）
        try:
            self.translator = MedicalTranslator()
            self.logger.info("翻译器初始化成功")
        except Exception as e:
            self.logger.warning(f"翻译器初始化失败: {e}，将使用内置词典")
            self.translator = None
        
    def setup_logging(self):
        """设置日志配置"""
        logging.basicConfig(
            level=logging.DEBUG,  # 改为DEBUG级别以显示调试信息
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('pancreatic_trials.log', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def search_studies(self, query: str, page_size: int = 50, phases: List[str] = None, status: List[str] = None, first_post_date: str = None, location: str = 'china') -> Dict[str, Any]:
        """
        搜索临床试验
        
        Args:
            query: 搜索查询字符串
            page_size: 每页返回的结果数量
            phases: 试验阶段列表 ['PHASE1', 'PHASE2', 'PHASE3', 'PHASE4', 'EARLY_PHASE1']
            status: 试验状态列表 ['RECRUITING', 'NOT_YET_RECRUITING', 'ACTIVE_NOT_RECRUITING']
            first_post_date: 首次发布日期过滤，格式如'2025-01-01'
            location: 地理位置过滤，如'china'
            
        Returns:
            API响应的JSON数据
        """
        # 构建基础参数 - 参考用户提供的正确curl示例
        params = {
            'format': 'json',
            'markupFormat': 'markdown',
            'query.cond': query,
            'countTotal': 'true',
            'pageSize': page_size
        }
        
        # 添加试验状态过滤 - 使用正确的API v2格式
        if status:
            # API v2使用逗号分隔的状态值
            params['filter.overallStatus'] = ','.join(status)
        else:
            params['filter.overallStatus'] = 'RECRUITING'
        
        # 添加开始日期过滤 - 使用postFilter.advanced参数
        if first_post_date:
            # 使用postFilter.advanced参数进行日期过滤，格式：AREA[StartDate]2025
            year = first_post_date.split('-')[0]  # 提取年份
            params['postFilter.advanced'] = f'AREA[StartDate]{year}'
        
        # 添加地理位置过滤
        if location:
            params['query.locn'] = location
        
        # 添加试验阶段过滤 - 使用aggFilters格式（参考curl示例）
        if phases:
            # 转换阶段格式为数字
            phase_numbers = []
            for phase in phases:
                if phase == '0' or phase == 'EARLY_PHASE1':
                    phase_numbers.append('0')
                elif phase == '1' or phase == 'PHASE1':
                    phase_numbers.append('1')
                elif phase == '2' or phase == 'PHASE2':
                    phase_numbers.append('2')
                elif phase == '3' or phase == 'PHASE3':
                    phase_numbers.append('3')
                elif phase == '4' or phase == 'PHASE4':
                    phase_numbers.append('4')
            if phase_numbers:
                # 使用aggFilters格式：status:rec,phase:4+3+2+1
                phase_filter = '+'.join(sorted(set(phase_numbers), reverse=True))
                params['aggFilters'] = f'status:rec,phase:{phase_filter}'
        else:
            # 默认包含所有阶段和招募状态
            params['aggFilters'] = 'status:rec,phase:4+3+2+1'
        
        try:
            self.logger.info(f"正在查询: {query}")
            # 手动构建URL以确保aggFilters参数中的+号不被编码为%2B
            from urllib.parse import urlencode, quote_plus
            
            # 分离aggFilters参数，单独处理
            agg_filters = params.pop('aggFilters', None)
            post_filter = params.pop('postFilter.advanced', None)
            base_params = urlencode(params, quote_via=quote_plus)
            
            # 构建完整URL，手动添加特殊参数
            full_url = f"{self.base_url}?{base_params}"
            
            if post_filter:
                # 添加postFilter.advanced参数，需要URL编码
                encoded_post_filter = post_filter.replace('[', '%5B').replace(']', '%5D')
                full_url += f"&postFilter.advanced={encoded_post_filter}"
            
            if agg_filters:
                # 手动添加aggFilters，保持+号不被编码，但编码冒号
                full_url += f"&aggFilters={agg_filters.replace(':', '%3A')}"
            
            self.logger.info(f"请求URL: {full_url}")
            response = self.session.get(full_url, timeout=30)
            self.logger.info(f"响应状态码: {response.status_code}")
            
            response.raise_for_status()
            
            data = response.json()
            total_count = data.get('totalCount', 0)
            self.logger.info(f"查询成功，返回 {total_count} 个结果")
            return data
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"API请求失败: {e}")
            raise
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON解析失败: {e}")
            raise
    
    def get_pancreatic_cancer_trials(self, search_keywords: str = None, first_post_date: str = None, days_back: int = 30, phases: List[str] = None, status: List[str] = None, location: str = 'china') -> List[Dict[str, Any]]:
        """
        获取胰腺癌相关的活跃临床试验
        
        Args:
            search_keywords: 搜索关键词，默认为胰腺癌相关术语
            first_post_date: 首次发布日期过滤 (YYYY-MM-DD格式)
            days_back: 向前查找的天数，默认30天
            phases: 试验阶段列表 ['0', '1', '2', '3', '4']
            status: 试验状态列表 ['RECRUITING', 'NOT_YET_RECRUITING', 'ACTIVE_NOT_RECRUITING']
            location: 地理位置过滤，如'china'
        
        Returns:
            符合条件的试验列表
        """
        # 构建搜索查询 - 优化查询策略：先用原词查询，失败后再翻译
        if search_keywords:
            query = search_keywords  # 先使用原词
        else:
            # 使用简化的查询条件，避免复杂的OR查询
            query = "pancreatic cancer"
        
        try:
            # 第一次尝试：使用原词搜索试验
            data = self.search_studies(query, phases=phases, status=status, first_post_date=first_post_date, location=location)
            
            # 检查查询结果是否有效
            if 'studies' not in data or len(data.get('studies', [])) == 0:
                # 如果原词查询无结果且包含中文，尝试翻译后重新查询
                if search_keywords and any('\u4e00' <= char <= '\u9fff' for char in search_keywords):
                    self.logger.info(f"原词 '{search_keywords}' 查询无结果，尝试翻译后重新查询")
                    translated_query = self._convert_chinese_to_english(search_keywords)
                    if translated_query != search_keywords:  # 确保翻译有效果
                        self.logger.info(f"使用翻译后的查询词重新搜索: '{translated_query}'")
                        data = self.search_studies(translated_query, phases=phases, status=status, first_post_date=first_post_date, location=location)
            else:
                self.logger.info(f"原词 '{query}' 查询成功，获得 {len(data.get('studies', []))} 个结果")
            
            # 保存完整的API响应数据到文件，供generate_report.py使用
            try:
                with open('api_response.json', 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                self.logger.info("API响应数据已保存到 api_response.json")
            except Exception as e:
                self.logger.warning(f"保存API响应数据失败: {e}")
            
            if 'studies' not in data:
                self.logger.warning("API响应中没有找到studies字段")
                return []
            
            studies = data['studies']
            self.logger.info(f"获取到 {len(studies)} 个试验")
            
            # 设置日期过滤条件
            if first_post_date:
                try:
                    cutoff_date = datetime.strptime(first_post_date, '%Y-%m-%d')
                    self.logger.info(f"使用用户指定的首次发布日期过滤: {first_post_date}")
                except ValueError:
                    self.logger.warning(f"日期格式错误，使用默认设置: {first_post_date}")
                    cutoff_date = datetime.now() - timedelta(days=days_back)
            else:
                cutoff_date = datetime.now() - timedelta(days=days_back)
            
            filtered_studies = []
            
            for study in studies:
                try:
                    # 检查最后更新日期
                    last_update_str = study.get('protocolSection', {}).get('statusModule', {}).get('lastUpdatePostDate', '')
                    if last_update_str:
                        # 解析日期格式 (ISO format)
                        last_update = datetime.fromisoformat(last_update_str.replace('Z', '+00:00'))
                        if last_update.replace(tzinfo=None) >= cutoff_date:
                            filtered_studies.append(study)
                            continue
                    
                    # 检查首次提交日期 (studyFirstSubmitDate)
                    first_submit_str = study.get('protocolSection', {}).get('statusModule', {}).get('studyFirstSubmitDate', '')
                    if first_submit_str:
                        # studyFirstSubmitDate 格式为 YYYY-MM-DD，不需要处理时区
                        first_submit = datetime.strptime(first_submit_str, '%Y-%m-%d')
                        if first_submit >= cutoff_date:
                            filtered_studies.append(study)
                            continue
                    
                    # 备用：检查首次发布日期结构 (studyFirstPostDateStruct)
                    first_post_struct = study.get('protocolSection', {}).get('statusModule', {}).get('studyFirstPostDateStruct', {})
                    if first_post_struct and 'date' in first_post_struct:
                        first_post_str = first_post_struct['date']
                        try:
                            first_post = datetime.strptime(first_post_str, '%Y-%m-%d')
                            if first_post >= cutoff_date:
                                filtered_studies.append(study)
                        except ValueError:
                            # 如果日期格式不是 YYYY-MM-DD，尝试 ISO 格式
                            first_post = datetime.fromisoformat(first_post_str.replace('Z', '+00:00'))
                            if first_post.replace(tzinfo=None) >= cutoff_date:
                                filtered_studies.append(study)
                            
                except Exception as e:
                    self.logger.warning(f"处理试验日期时出错: {e}")
                    # 如果日期解析失败，仍然包含该试验
                    filtered_studies.append(study)
            
            self.logger.info(f"日期过滤后剩余 {len(filtered_studies)} 个试验")
            return filtered_studies
                
        except Exception as e:
            self.logger.error(f"搜索试验时发生错误: {e}")
            return []
    
    def _convert_chinese_to_english(self, search_keywords: str) -> str:
        """将中文查询词转换为英文
        
        Args:
            search_keywords: 用户输入的查询词
            
        Returns:
            转换后的英文查询词
        """
        # 检查是否包含中文字符
        if not any('\u4e00' <= char <= '\u9fff' for char in search_keywords):
            # 如果不包含中文，直接返回原词
            return search_keywords
        
        # 优先使用翻译器进行转换
        if self.translator:
            try:
                # 创建专门的翻译提示词
                translation_prompt = (
                    "你是一个专业的医学翻译专家。请将以下中文医学查询词翻译成英文，"
                    "要求：1. 保持医学术语的准确性；2. 适合用于临床试验数据库搜索；"
                    "3. 只返回翻译结果，不要添加任何解释。\n\n"
                    f"请翻译：{search_keywords}"
                )
                
                # 使用翻译器进行翻译
                result = self.translator.translate_text(translation_prompt)
                translated = result.translated.strip()
                
                self.logger.info(f"使用翻译器转换查询词: '{search_keywords}' -> '{translated}'")
                return translated
                
            except Exception as e:
                self.logger.warning(f"翻译器转换失败: {e}，使用内置词典")
        
        # 备选方案：使用内置词典
        chinese_to_english = {
            "胰腺癌": "pancreatic cancer",
            "胰腺腺癌": "pancreatic adenocarcinoma", 
            "胰腺导管腺癌": "pancreatic ductal adenocarcinoma",
            "胰腺肿瘤": "pancreatic tumor",
            "胰腺肿瘤": "pancreatic neoplasm",
            "胰腺癌免疫治疗": "pancreatic cancer immunotherapy",
            "胰腺癌化疗": "pancreatic cancer chemotherapy",
            "胰腺癌靶向治疗": "pancreatic cancer targeted therapy",
            "胰腺癌手术": "pancreatic cancer surgery",
            "胰腺癌放疗": "pancreatic cancer radiotherapy"
        }
        
        if search_keywords in chinese_to_english:
            translated = chinese_to_english[search_keywords]
            self.logger.info(f"使用内置词典转换查询词: '{search_keywords}' -> '{translated}'")
            return translated
        else:
            # 如果词典中没有，返回原词并记录警告
            self.logger.warning(f"未找到查询词 '{search_keywords}' 的英文翻译，使用原词")
            return search_keywords
    
    def get_pancreatic_cancer_trials_with_report(
        self, 
        search_keywords: str = None,
        first_post_date: str = None,
        days_back: int = 365,
        phases: List[str] = None,
        status: List[str] = None,
        location: str = None
    ) -> str:
        """获取胰腺癌临床试验数据并生成报告
        
        Args:
            search_keywords: 搜索关键词
            first_post_date: 首次发布日期过滤 (YYYY-MM-DD)
            days_back: 向前查询天数
            phases: 试验阶段列表
            status: 试验状态列表
            location: 地理位置
            
        Returns:
            生成的报告文件名
        """
        self.logger.info("开始获取胰腺癌临床试验数据")
        
        # 调用原有的get_pancreatic_cancer_trials方法获取数据
        filtered_studies = self.get_pancreatic_cancer_trials(
            search_keywords=search_keywords,
            first_post_date=first_post_date,
            days_back=days_back,
            phases=phases,
            status=status,
            location=location
        )
        
        if not filtered_studies:
            self.logger.warning("未找到符合条件的临床试验")
            return None
        
        # 生成报告
        try:
            # 直接调用generate_report函数
            generate_report()
            self.logger.info("报告生成完成")
            
            # 准备返回数据
            report_data = {
                'studies': filtered_studies,
                'search_params': {
                    'search_keywords': search_keywords,
                    'first_post_date': first_post_date,
                    'days_back': days_back,
                    'phases': phases,
                    'status': status,
                    'location': location
                },
                'total_count': len(filtered_studies),
                'query_time': datetime.now().isoformat()
            }
            
            # 生成报告文件
            report_filename = report_generator.generate_report(report_data)
            self.logger.info(f"报告已生成: {report_filename}")
            
            return report_filename
            
        except Exception as e:
            self.logger.error(f"生成报告时发生错误: {e}")
            return None
    
    def format_study_to_markdown(self, study: Dict[str, Any]) -> str:
        """
        将试验数据格式化为Markdown
        
        Args:
            study: 试验数据字典
            
        Returns:
            格式化的Markdown字符串
        """
        try:
            protocol = study.get('protocolSection', {})
            identification = protocol.get('identificationModule', {})
            status = protocol.get('statusModule', {})
            design = protocol.get('designModule', {})
            arms = protocol.get('armsInterventionsModule', {})
            contacts = protocol.get('contactsLocationsModule', {})
            eligibility = protocol.get('eligibilityModule', {})
            
            # 基本信息
            nct_id = identification.get('nctId', 'N/A')
            brief_title = identification.get('briefTitle', 'N/A')
            official_title = identification.get('officialTitle', brief_title)
            
            # 翻译关键信息
            brief_title_zh = self._translate_text(brief_title, 'title') if self.translator else None
            official_title_zh = self._translate_text(official_title, 'title') if self.translator else None
            
            # 状态信息
            overall_status = status.get('overallStatus', 'N/A')
            study_type = design.get('studyType', 'N/A')
            phases = design.get('phases', [])
            phase = ', '.join(phases) if phases else 'N/A'
            
            # 疾病条件
            conditions = protocol.get('conditionsModule', {}).get('conditions', [])
            condition_str = ', '.join(conditions) if conditions else 'N/A'
            condition_str_zh = self._translate_text(condition_str, 'conditions') if self.translator else None
            
            # 干预措施
            interventions = arms.get('interventions', [])
            intervention_names = []
            intervention_types = []
            for intervention in interventions:
                intervention_names.append(intervention.get('name', 'N/A'))
                intervention_types.append(intervention.get('type', 'N/A'))
            
            intervention_names_str = ', '.join(intervention_names)
            intervention_types_str = ', '.join(intervention_types)
            intervention_names_zh = self._translate_text(intervention_names_str, 'interventions') if self.translator else None
            intervention_types_zh = self._translate_text(intervention_types_str, 'interventions') if self.translator else None
            
            # 发起方信息
            sponsor = protocol.get('sponsorCollaboratorsModule', {})
            lead_sponsor = sponsor.get('leadSponsor', {}).get('name', 'N/A')
            
            # 地点信息
            locations = contacts.get('locations', [])
            location_strs = []
            for location in locations[:3]:  # 只显示前3个地点
                facility = location.get('facility', 'N/A')
                city = location.get('city', '')
                country = location.get('country', '')
                location_str = f"{facility}"
                if city:
                    location_str += f", {city}"
                if country:
                    location_str += f", {country}"
                location_strs.append(location_str)
            
            # 日期信息
            start_date = status.get('startDate', {}).get('date', 'N/A')
            completion_date = status.get('primaryCompletionDate', {}).get('date', 'N/A')
            # 使用首次提交日期而不是首次发布日期
            first_submit_date = status.get('studyFirstSubmitDate', 'N/A')
            # 备用：如果没有提交日期，使用发布日期结构
            if first_submit_date == 'N/A':
                first_submit_date = status.get('studyFirstPostDateStruct', {}).get('date', 'N/A')
            last_update_date = status.get('lastUpdatePostDate', {}).get('date', 'N/A')
            
            # 招募信息
            enrollment = design.get('enrollmentInfo', {}).get('count', 'N/A')
            
            # 联系信息 - 优先使用centralContacts，备用overallContacts
            central_contacts = contacts.get('centralContacts', [])
            overall_contacts = contacts.get('overallContacts', [])
            contact_name = 'N/A'
            contact_phone = 'N/A'
            contact_email = 'N/A'
            
            # 优先使用centralContacts
            if central_contacts:
                contact = central_contacts[0]
                contact_name = contact.get('name', 'N/A')
                contact_phone = contact.get('phone', 'N/A')
                contact_email = contact.get('email', 'N/A')
            # 如果没有centralContacts，使用overallContacts作为备用
            elif overall_contacts:
                contact = overall_contacts[0]
                contact_name = contact.get('name', 'N/A')
                contact_phone = contact.get('phone', 'N/A')
                contact_email = contact.get('email', 'N/A')
            
            # 构建Markdown（中英文对照）
            title_display = self._format_bilingual_text(brief_title, brief_title_zh)
            official_title_display = self._format_bilingual_text(official_title, official_title_zh)
            condition_display = self._format_bilingual_text(condition_str, condition_str_zh)
            intervention_names_display = self._format_bilingual_text(intervention_names_str, intervention_names_zh)
            intervention_types_display = self._format_bilingual_text(intervention_types_str, intervention_types_zh)
            
            markdown = f"""## {title_display}

**试验编号**: {nct_id}  
**正式标题**: {official_title_display}  
**疾病条件**: {condition_display}  
**试验状态**: {overall_status}  
**试验阶段**: {phase}  
**研究类型**: {study_type}  

### 干预措施
**干预名称**: {intervention_names_display}  
**干预类型**: {intervention_types_display}  

### 试验信息
**主要发起方**: {lead_sponsor}  
**试验地点**: {'; '.join(location_strs)}  
**开始日期**: {start_date}  
**预计完成日期**: {completion_date}  
**招募人数**: {enrollment}  

### 重要日期
**首次提交**: {first_submit_date}  
**最后更新**: {last_update_date}  

### 联系信息
**联系人**: {contact_name}  
**电话**: {contact_phone}  
**邮箱**: {contact_email}  

**试验链接**: [ClinicalTrials.gov](https://clinicaltrials.gov/study/{nct_id})

---

"""
            
            # 调试信息：检查生成的markdown长度
            self.logger.debug(f"生成的markdown长度: {len(markdown)} 字符")
            if len(markdown) < 100:
                self.logger.warning(f"生成的markdown内容过短: {markdown[:200]}...")
            
            return markdown
            
        except Exception as e:
            self.logger.error(f"格式化试验数据时出错: {e}")
            return f"## 数据格式化错误\n\n试验ID: {study.get('protocolSection', {}).get('identificationModule', {}).get('nctId', 'Unknown')}\n\n---\n\n"
    
    def _translate_text(self, text: str, field_type: str) -> Optional[str]:
        """翻译文本"""
        if not self.translator or not text or text == 'N/A':
            return None
        
        try:
            # 对于短文本或单个词，可能不需要翻译
            if len(text.strip()) < 3:
                return None
            
            # 过滤可能导致异常翻译的单词
            # 如果是单个常见医学术语，跳过翻译
            single_word_terms = ['DRUG', 'DRUGS', 'MEDICATION', 'THERAPY', 'TREATMENT', 'STUDY', 'TRIAL', 'CLINICAL']
            if text.strip().upper() in single_word_terms:
                self.logger.info(f"跳过单个医学术语的翻译: {text}")
                return None
            
            translated = self.translator.translate(text)
            
            # 检查翻译结果是否异常
            if translated and (len(translated) > len(text) * 10 or translated.count('\n') > 20):
                self.logger.warning(f"检测到异常翻译结果，跳过: 原文='{text}', 翻译长度={len(translated)}")
                return None
                
            return translated if translated != text else None
        except Exception as e:
            self.logger.warning(f"翻译失败 ({field_type}): {e}")
            return None
    
    def _format_bilingual_text(self, original: str, translated: Optional[str]) -> str:
        """格式化双语文本"""
        if not translated or translated == original:
            return original
        
        # 过滤异常长的翻译内容（可能是词汇表）
        # 如果翻译内容比原文长度超过10倍，或者包含大量换行符，则认为是异常翻译
        newline_count = translated.count('\n')
        if (len(translated) > len(original) * 10) or (newline_count > 20):
            self.logger.warning(f"检测到异常翻译内容，使用原文: 原文长度={len(original)}, 翻译长度={len(translated)}, 换行数={newline_count}")
            return original
        
        # 如果翻译文本过长，使用折叠格式
        if len(translated) > 100:
            return f"{translated}\n\n<details>\n<summary>🔍 查看英文原文</summary>\n\n{original}\n\n</details>"
        else:
            return f"{translated} ({original})"
    
    def save_studies_to_markdown(self, studies: List[Dict[str, Any]], filename: str = None, search_keywords: str = None) -> str:
        """
        将试验数据保存为Markdown格式文件
        
        Args:
            studies: 试验数据列表
            filename: 输出文件名，如果为None则自动生成
            search_keywords: 搜索关键词，用于生成文件名和报告标题
            
        Returns:
            保存的文件路径
        """
        if filename is None:
            today = datetime.now().strftime('%Y-%m-%d')
            if search_keywords:
                # 清理关键词用于文件名
                clean_keywords = search_keywords.replace(' ', '_').replace('/', '_').replace('\\', '_').replace(':', '_').replace('*', '_').replace('?', '_').replace('"', '_').replace('<', '_').replace('>', '_').replace('|', '_')
                # 限制长度避免文件名过长
                if len(clean_keywords) > 20:
                    clean_keywords = clean_keywords[:20]
                filename = f"{today}_{clean_keywords}_临床试验.md"
            else:
                filename = f"{today}_胰腺癌临床试验.md"
        
        # 按状态分组
        recruiting_studies = []
        active_studies = []
        other_studies = []  # 其他状态的试验
        
        self.logger.info(f"开始对 {len(studies)} 个试验进行状态分组")
        
        for i, study in enumerate(studies):
            status = study.get('protocolSection', {}).get('statusModule', {}).get('overallStatus', '')
            status_upper = status.upper()  # 转换为大写进行比较
            nct_id = study.get('protocolSection', {}).get('identificationModule', {}).get('nctId', 'Unknown')
            
            self.logger.info(f"试验 {i+1}/{len(studies)}: {nct_id}, 状态: '{status}' -> '{status_upper}'")
            
            if 'RECRUITING' in status_upper:
                recruiting_studies.append(study)
                self.logger.info(f"  -> 分组到: 招募中")
            elif 'ACTIVE' in status_upper:
                active_studies.append(study)
                self.logger.info(f"  -> 分组到: 活跃")
            else:
                other_studies.append(study)  # 收集其他状态的试验
                self.logger.info(f"  -> 分组到: 其他")
        
        # 调试信息：显示分组结果
        self.logger.info(f"试验分组结果: 招募中={len(recruiting_studies)}, 活跃={len(active_studies)}, 其他={len(other_studies)}")
        
        # 生成Markdown内容
        translation_status = "✅ 已启用" if self.translator else "❌ 未启用"
        # 动态生成报告标题
        report_title = f"{search_keywords}临床试验报告" if search_keywords else "胰腺癌临床试验报告"
        query_condition = search_keywords if search_keywords else "胰腺癌"
        
        content = f"""# {report_title}

**生成日期**: {datetime.now().strftime('%Y-%m-%d')}
**查询条件**: {query_condition}相关的活跃临床试验
**查询范围**: 最近30天内新增或更新的试验
**试验总数**: {len(studies)}
**智能翻译**: {translation_status}

> 📝 **说明**: 本报告提供中英文对照信息，关键医学术语保持原文以确保准确性。

## 试验列表

"""
        
        self.logger.info(f"开始生成试验列表内容")
        
        if recruiting_studies:
            self.logger.info(f"添加 {len(recruiting_studies)} 个招募中的试验")
            content += "### 正在招募的试验\n\n"
            for i, study in enumerate(recruiting_studies):
                self.logger.info(f"格式化招募中试验 {i+1}/{len(recruiting_studies)}")
                study_content = self.format_study_to_markdown(study)
                content += study_content
                self.logger.info(f"试验内容长度: {len(study_content)} 字符")
        
        if active_studies:
            self.logger.info(f"添加 {len(active_studies)} 个活跃试验")
            content += "### 活跃但未招募的试验\n\n"
            for i, study in enumerate(active_studies):
                self.logger.info(f"格式化活跃试验 {i+1}/{len(active_studies)}")
                study_content = self.format_study_to_markdown(study)
                content += study_content
                self.logger.info(f"试验内容长度: {len(study_content)} 字符")
        
        if other_studies:
            self.logger.info(f"添加 {len(other_studies)} 个其他状态试验")
            content += "### 其他状态的试验\n\n"
            for i, study in enumerate(other_studies):
                self.logger.info(f"格式化其他状态试验 {i+1}/{len(other_studies)}")
                study_content = self.format_study_to_markdown(study)
                content += study_content
                self.logger.info(f"试验内容长度: {len(study_content)} 字符")
        
        if not studies:
            condition_name = search_keywords if search_keywords else "胰腺癌"
            content += f"### 暂无符合条件的试验\n\n在最近30天内没有找到新增或更新的{condition_name}临床试验。\n"
            self.logger.info("添加了'暂无试验'的内容")
        
        self.logger.info(f"最终内容总长度: {len(content)} 字符")
        
        # 保存文件
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(content)
            
            self.logger.info(f"报告已保存到: {filename}")
            return filename
            
        except Exception as e:
            self.logger.error(f"保存文件失败: {e}")
            raise
    
    def run(self, search_keywords: str = None, first_post_date: str = None, days_back: int = 30, phases: List[str] = None, status: List[str] = None, location: str = "china") -> str:
        """
        运行主程序
        
        Args:
            search_keywords: 搜索关键词
            first_post_date: 首次发布日期过滤
            days_back: 向前查找的天数
            phases: 试验阶段列表
            status: 试验状态列表
            location: 地理位置过滤 (如: 'china', 'united states')
        
        Returns:
            生成的报告文件路径
        """
        try:
            self.logger.info("开始执行胰腺癌临床试验查询")
            
            # 获取试验数据
            studies = self.get_pancreatic_cancer_trials(search_keywords, first_post_date, days_back, phases, status, location)
            
            # 保存为Markdown文件
            filename = self.save_studies_to_markdown(studies, search_keywords=search_keywords)
            
            self.logger.info(f"程序执行完成，共找到 {len(studies)} 个符合条件的试验")
            return filename
            
        except Exception as e:
            self.logger.error(f"程序执行失败: {e}")
            raise

def get_user_input():
    """
    获取用户输入的查询参数
    
    Returns:
        tuple: (search_keywords, first_post_date, days_back, phases, status)
    """
    print("\n" + "="*60)
    print("🔬 胰腺癌临床试验智能查询系统")
    print("="*60)
    print("\n📋 系统功能说明:")
    print("• 查询范围: 1期到4期的临床试验")
    print("• 默认查询周期: 最近30天内新增或更新的试验")
    print("• 支持中英文对照显示 (需配置翻译功能)")
    print("• 输出格式: Markdown报告文件")
    
    print("\n" + "-"*50)
    print("📝 请输入查询条件 (直接回车使用默认值):")
    
    # 获取搜索关键词
    print("\n1️⃣ 检索关键词:")
    print("   默认: 胰腺癌相关术语 (pancreatic cancer, PDAC等)")
    print("   示例: 'pancreatic cancer immunotherapy' 或 '胰腺癌免疫治疗'")
    search_keywords = input("   请输入关键词: ").strip()
    if not search_keywords:
        search_keywords = None
        print("   ✓ 使用默认胰腺癌相关术语")
    else:
        print(f"   ✓ 使用关键词: {search_keywords}")
    
    # 获取首次发布日期
    print("\n2️⃣ 首次发布日期过滤:")
    print("   格式: YYYY-MM-DD (例如: 2025-01-01)")
    print("   说明: 查找此日期之后首次发布的试验")
    print("   默认: 2025-01-01")
    first_post_date = input("   请输入日期 (回车使用默认): ").strip()
    if not first_post_date:
        first_post_date = "2025-01-01"
        print("   ✓ 使用默认首次发布日期: 2025-01-01")
    else:
        # 验证日期格式
        try:
            datetime.strptime(first_post_date, '%Y-%m-%d')
            print(f"   ✓ 使用首次发布日期: {first_post_date}")
        except ValueError:
            print("   ❌ 日期格式错误，将使用默认设置")
            first_post_date = None
    
    # 获取查询天数
    print("\n3️⃣ 查询时间范围:")
    print("   默认: 30天 (查找最近30天内的试验)")
    print("   建议: 7-90天之间")
    days_input = input("   请输入天数: ").strip()
    if not days_input:
        days_back = 30
        print("   ✓ 使用默认30天")
    else:
        try:
            days_back = int(days_input)
            if days_back <= 0:
                days_back = 30
                print("   ❌ 天数必须大于0，使用默认30天")
            else:
                print(f"   ✓ 使用{days_back}天")
        except ValueError:
            days_back = 30
            print("   ❌ 输入格式错误，使用默认30天")
    
    # 获取试验阶段
    print("\n4️⃣ 试验阶段选择:")
    print("   0: 0期 (早期1期), 1: 1期, 2: 2期, 3: 3期, 4: 4期")
    print("   默认: 包含所有阶段 (0-4期)")
    phases_input = input("   请输入阶段 (如: 1,2,3 或回车选择全部): ").strip()
    phases = None
    if phases_input:
        try:
            phases = [p.strip() for p in phases_input.split(',') if p.strip() in ['0', '1', '2', '3', '4']]
            if phases:
                print(f"   ✓ 选择阶段: {', '.join([f'{p}期' for p in phases])}")
            else:
                phases = None
                print("   ❌ 输入格式错误，使用默认全部阶段")
        except:
            phases = None
            print("   ❌ 输入格式错误，使用默认全部阶段")
    else:
        print("   ✓ 使用默认全部阶段 (0-4期)")
    
    # 获取试验状态
    print("\n5️⃣ 试验状态选择:")
    print("   RECRUITING: 招募中")
    print("   NOT_YET_RECRUITING: 尚未开始招募")
    print("   ACTIVE_NOT_RECRUITING: 活跃但不招募")
    print("   默认: 仅招募中的试验")
    status_input = input("   请输入状态 (如: RECRUITING 或回车使用默认): ").strip()
    status = None
    if status_input:
        valid_status = ['RECRUITING', 'NOT_YET_RECRUITING', 'ACTIVE_NOT_RECRUITING']
        status_list = [s.strip().upper() for s in status_input.replace(',', ' ').split() if s.strip().upper() in valid_status]
        if status_list:
            status = status_list
            status_names = {
                'RECRUITING': '招募中',
                'NOT_YET_RECRUITING': '尚未开始招募', 
                'ACTIVE_NOT_RECRUITING': '活跃但不招募'
            }
            status_desc = [status_names[s] for s in status]
            print(f"   ✓ 选择状态: {', '.join(status_desc)}")
        else:
            print("   ❌ 输入格式错误，使用默认仅招募中")
    else:
        print("   ✓ 使用默认仅招募中的试验")
    
    # 获取地区国家
    print("\n6️⃣ 地区国家选择:")
    print("   常用选项:")
    print("   • china: 中国")
    print("   • united states: 美国")
    print("   • japan: 日本")
    print("   • korea: 韩国")
    print("   • singapore: 新加坡")
    print("   • australia: 澳大利亚")
    print("   • canada: 加拿大")
    print("   • united kingdom: 英国")
    print("   默认: china (中国)")
    location_input = input("   请输入地区/国家 (英文名称，回车使用默认): ").strip()
    if not location_input:
        location = "china"
        print("   ✓ 使用默认地区: 中国 (china)")
    else:
        location = location_input.lower()
        print(f"   ✓ 使用地区: {location}")
    
    return search_keywords, first_post_date, days_back, phases, status, location

def main():
    """主函数"""
    try:
        # 获取用户输入
        search_keywords, first_post_date, days_back, phases, status, location = get_user_input()
        
        print("\n" + "-"*50)
        print("🚀 开始查询临床试验...")
        
        # 创建查询器并执行
        finder = PancreaticCancerTrialsFinder()
        filename = finder.run(search_keywords, first_post_date, days_back, phases, status, location)
        
        print("\n" + "="*60)
        print("✅ 查询完成！")
        print(f"📄 报告已保存到: {filename}")
        print("\n💡 提示:")
        print("• 报告包含试验的详细信息和联系方式")
        print("• 如需翻译功能，请配置config.json文件")
        print("• 建议定期运行以获取最新试验信息")
        print("="*60)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  用户取消操作")
        return 1
    except Exception as e:
        print(f"\n❌ 程序执行失败: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())