#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基于API响应生成胰腺癌临床试验报告
集成API调用和日期过滤逻辑
"""

import json
import requests
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import time
import os
from urllib.parse import urlencode, quote_plus

def setup_logging():
    """设置日志配置"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('pancreatic_trials.log', encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

def search_studies(query: str, page_size: int = 50, phases: List[str] = None, status: List[str] = None, first_post_date: str = None, location: str = None, logger=None) -> Dict[str, Any]:
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
    base_url = "https://beta-ut.clinicaltrials.gov/api/v2/studies"
    
    # 构建基础参数
    params = {
        'format': 'json',
        'markupFormat': 'markdown',
        'query.cond': query,
        'countTotal': 'true',
        'pageSize': page_size
    }
    
    # 添加试验状态过滤
    if status:
        params['filter.overallStatus'] = ','.join(status)
    else:
        params['filter.overallStatus'] = 'RECRUITING'
    
    # 添加开始日期过滤
    if first_post_date:
        year = first_post_date.split('-')[0]  # 提取年份
        params['postFilter.advanced'] = f'AREA[StartDate]{year}'
    
    # 添加地理位置过滤
    if location:
        params['query.locn'] = location
    
    # 添加试验阶段过滤
    if phases:
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
            phase_filter = '+'.join(sorted(set(phase_numbers), reverse=True))
            params['aggFilters'] = f'status:rec,phase:{phase_filter}'
    else:
        params['aggFilters'] = 'status:rec,phase:4+3+2+1'
    
    try:
        if logger:
            logger.info(f"正在查询: {query}")
        
        # 构建URL
        agg_filters = params.pop('aggFilters', None)
        post_filter = params.pop('postFilter.advanced', None)
        base_params = urlencode(params, quote_via=quote_plus)
        
        full_url = f"{base_url}?{base_params}"
        
        if post_filter:
            encoded_post_filter = post_filter.replace('[', '%5B').replace(']', '%5D')
            full_url += f"&postFilter.advanced={encoded_post_filter}"
        
        if agg_filters:
            full_url += f"&aggFilters={agg_filters.replace(':', '%3A')}"
        
        if logger:
            logger.info(f"请求URL: {full_url}")
        
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'PancreaticCancerTrialsFinder/1.0'
        })
        
        response = session.get(full_url, timeout=30)
        
        if logger:
            logger.info(f"响应状态码: {response.status_code}")
        
        response.raise_for_status()
        
        data = response.json()
        total_count = data.get('totalCount', 0)
        
        if logger:
            logger.info(f"查询成功，返回 {total_count} 个结果")
        
        return data
        
    except requests.exceptions.RequestException as e:
        if logger:
            logger.error(f"API请求失败: {e}")
        raise
    except json.JSONDecodeError as e:
        if logger:
            logger.error(f"JSON解析失败: {e}")
        raise

def get_pancreatic_cancer_trials(search_keywords: str = None, first_post_date: str = None, days_back: int = 30, phases: List[str] = None, status: List[str] = None, location: str = None, logger=None) -> List[Dict[str, Any]]:
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
    # 构建搜索查询
    if search_keywords:
        query = search_keywords
    else:
        query = "pancreatic cancer"
    
    try:
        # 搜索试验
        data = search_studies(query, phases=phases, status=status, first_post_date=first_post_date, location=location, logger=logger)
        
        if 'studies' not in data:
            if logger:
                logger.warning("API响应中没有找到studies字段")
            return []
        
        studies = data['studies']
        if logger:
            logger.info(f"获取到 {len(studies)} 个试验")
        
        # 设置日期过滤条件
        if first_post_date:
            try:
                cutoff_date = datetime.strptime(first_post_date, '%Y-%m-%d')
                if logger:
                    logger.info(f"使用用户指定的首次发布日期过滤: {first_post_date}")
            except ValueError:
                if logger:
                    logger.warning(f"日期格式错误，使用默认设置: {first_post_date}")
                cutoff_date = datetime.now() - timedelta(days=days_back)
        else:
            cutoff_date = datetime.now() - timedelta(days=days_back)
        
        filtered_studies = []
        
        for study in studies:
            try:
                # 检查最后更新日期
                last_update_str = study.get('protocolSection', {}).get('statusModule', {}).get('lastUpdatePostDate', '')
                if last_update_str:
                    last_update = datetime.fromisoformat(last_update_str.replace('Z', '+00:00'))
                    if last_update.replace(tzinfo=None) >= cutoff_date:
                        filtered_studies.append(study)
                        continue
                
                # 检查首次提交日期 (studyFirstSubmitDate) - 优先使用
                first_submit_str = study.get('protocolSection', {}).get('statusModule', {}).get('studyFirstSubmitDate', '')
                if first_submit_str:
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
                        first_post = datetime.fromisoformat(first_post_str.replace('Z', '+00:00'))
                        if first_post.replace(tzinfo=None) >= cutoff_date:
                            filtered_studies.append(study)
                        
            except Exception as e:
                if logger:
                    logger.warning(f"处理试验日期时出错: {e}")
                # 如果日期解析失败，仍然包含该试验
                filtered_studies.append(study)
        
        if logger:
            logger.info(f"日期过滤后剩余 {len(filtered_studies)} 个试验")
        
        return filtered_studies
            
    except Exception as e:
        if logger:
            logger.error(f"搜索试验时发生错误: {e}")
        return []

def load_api_response():
    """加载API响应数据（保持向后兼容）"""
    try:
        with open('api_response.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print("未找到api_response.json文件")
        return None

def format_study_to_markdown(study):
    """将单个研究格式化为Markdown"""
    protocol = study.get('protocolSection', {})
    identification = protocol.get('identificationModule', {})
    status = protocol.get('statusModule', {})
    design = protocol.get('designModule', {})
    conditions = protocol.get('conditionsModule', {})
    interventions = protocol.get('armsInterventionsModule', {})
    contacts = protocol.get('contactsLocationsModule', {})
    eligibility = protocol.get('eligibilityModule', {})
    
    # 基本信息
    nct_id = identification.get('nctId', 'N/A')
    title = identification.get('briefTitle', 'N/A')
    overall_status = status.get('overallStatus', 'N/A')
    
    # 条件
    condition_list = conditions.get('conditions', [])
    condition_str = ', '.join(condition_list) if condition_list else 'N/A'
    
    # 干预措施
    intervention_list = interventions.get('interventions', [])
    intervention_names = []
    for intervention in intervention_list:
        name = intervention.get('name', '')
        if name:
            intervention_names.append(name)
    intervention_str = ', '.join(intervention_names) if intervention_names else 'N/A'
    
    # 申办方
    sponsor_module = protocol.get('sponsorCollaboratorsModule', {})
    lead_sponsor = sponsor_module.get('leadSponsor', {})
    sponsor_name = lead_sponsor.get('name', 'N/A')
    
    # 地点
    locations = contacts.get('locations', [])
    location_names = []
    for location in locations[:3]:  # 只显示前3个地点
        facility = location.get('facility', '')
        city = location.get('city', '')
        country = location.get('country', '')
        if facility or city:
            loc_str = f"{facility}, {city}, {country}" if facility else f"{city}, {country}"
            location_names.append(loc_str)
    location_str = '; '.join(location_names) if location_names else 'N/A'
    
    # 入组标准
    criteria = eligibility.get('eligibilityCriteria', 'N/A')
    if len(criteria) > 200:
        criteria = criteria[:200] + '...'
    
    # 联系信息
    overall_officials = contacts.get('overallOfficials', [])
    contact_info = 'N/A'
    if overall_officials:
        official = overall_officials[0]
        name = official.get('name', '')
        affiliation = official.get('affiliation', '')
        if name:
            contact_info = f"{name}" + (f" ({affiliation})" if affiliation else "")
    
    # 开始日期
    start_date = status.get('startDateStruct', {}).get('date', 'N/A')
    
    # 首次提交日期 (优先使用studyFirstSubmitDate)
    first_submit_date = status.get('studyFirstSubmitDate', '')
    if not first_submit_date:
        # 备用：使用studyFirstPostDateStruct
        first_post_struct = status.get('studyFirstPostDateStruct', {})
        first_submit_date = first_post_struct.get('date', 'N/A')
    
    markdown = f"""
#### {title}

- **试验编号**: {nct_id}
- **状态**: {overall_status}
- **适应症**: {condition_str}
- **干预措施**: {intervention_str}
- **申办方**: {sponsor_name}
- **研究地点**: {location_str}
- **开始日期**: {start_date}
- **首次提交**: {first_submit_date}
- **主要研究者**: {contact_info}
- **入组标准**: {criteria}
- **详细信息**: https://clinicaltrials.gov/study/{nct_id}

---

"""
    return markdown

def generate_report(search_keywords: str = None, first_post_date: str = '2025-01-01', days_back: int = 30, phases: List[str] = None, status: List[str] = None, location: str = None, use_api: bool = True):
    """
    生成报告
    
    Args:
        search_keywords: 搜索关键词，默认为胰腺癌相关术语
        first_post_date: 首次发布日期过滤 (YYYY-MM-DD格式)
        days_back: 向前查找的天数，默认30天
        phases: 试验阶段列表 ['0', '1', '2', '3', '4']
        status: 试验状态列表 ['RECRUITING', 'NOT_YET_RECRUITING', 'ACTIVE_NOT_RECRUITING']
        location: 地理位置过滤，如'china'
        use_api: 是否直接调用API，默认True；False时从api_response.json读取
    """
    # 设置日志
    logger = setup_logging()
    
    if use_api:
        # 直接调用API获取最新数据
        logger.info("直接调用API获取最新数据")
        studies = get_pancreatic_cancer_trials(
            search_keywords=search_keywords,
            first_post_date=first_post_date,
            days_back=days_back,
            phases=phases,
            status=status,
            location=location,
            logger=logger
        )
        
        if not studies:
            logger.warning("未获取到任何试验数据")
            print("❌ 未获取到任何试验数据")
            return
        
        # 构建数据结构以兼容原有逻辑
        data = {
            'studies': studies,
            'totalCount': len(studies)
        }
        total_count = len(studies)
        
        # 保存API响应数据到文件
        try:
            with open('api_response.json', 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info("API响应数据已保存到 api_response.json")
        except Exception as e:
            logger.warning(f"保存API响应数据失败: {e}")
    else:
        # 从文件读取数据（向后兼容）
        logger.info("从api_response.json文件读取数据")
        data = load_api_response()
        if not data:
            logger.error("未找到api_response.json文件")
            print("❌ 未找到api_response.json文件")
            return
        
        studies = data.get('studies', [])
        total_count = data.get('totalCount', 0)
    
    # 生成报告
    current_date = datetime.now().strftime('%Y-%m-%d')
    
    # 根据搜索关键词生成文件名
    if search_keywords:
        # 清理搜索关键词，移除特殊字符，用于文件名
        clean_keywords = search_keywords.replace(' ', '_').replace('/', '_').replace('\\', '_').replace(':', '_').replace('*', '_').replace('?', '_').replace('"', '_').replace('<', '_').replace('>', '_').replace('|', '_')
        # 限制文件名长度
        if len(clean_keywords) > 30:
            clean_keywords = clean_keywords[:30]
        filename = f"{current_date}_{clean_keywords}_临床试验报告.md"
        report_title = f"{search_keywords}临床试验报告"
    else:
        filename = f"{current_date}_胰腺癌临床试验报告.md"
        report_title = "胰腺癌临床试验报告"
    
    content = f"""# {report_title}

**生成日期**: {current_date}
**数据来源**: ClinicalTrials.gov API v2
**查询条件**: {search_keywords if search_keywords else '胰腺癌'}相关的活跃临床试验
**总计试验数**: {total_count}
**本次显示**: {len(studies)} 个试验

---

## 试验列表

"""
    
    # 按状态分组
    recruiting_studies = []
    active_studies = []
    other_studies = []
    
    for study in studies:
        status = study.get('protocolSection', {}).get('statusModule', {}).get('overallStatus', '')
        if 'RECRUITING' in status.upper():
            recruiting_studies.append(study)
        elif 'ACTIVE' in status.upper():
            active_studies.append(study)
        else:
            other_studies.append(study)
    
    # 添加招募中的试验
    if recruiting_studies:
        content += f"### 正在招募 ({len(recruiting_studies)} 个试验)\n\n"
        for study in recruiting_studies:
            content += format_study_to_markdown(study)
    
    # 添加活跃但不招募的试验
    if active_studies:
        content += f"### 活跃但不招募 ({len(active_studies)} 个试验)\n\n"
        for study in active_studies:
            content += format_study_to_markdown(study)
    
    # 添加其他状态的试验
    if other_studies:
        content += f"### 其他状态 ({len(other_studies)} 个试验)\n\n"
        for study in other_studies:
            content += format_study_to_markdown(study)
    
    # 保存文件
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✅ 报告已生成: {filename}")
        print(f"📊 总计 {total_count} 个试验，本次处理 {len(studies)} 个")
        print(f"📋 招募中: {len(recruiting_studies)} 个")
        print(f"📋 活跃但不招募: {len(active_studies)} 个")
        print(f"📋 其他状态: {len(other_studies)} 个")
        
    except Exception as e:
        print(f"❌ 保存文件失败: {e}")

if __name__ == "__main__":
    # 使用默认参数生成报告
    # 可以根据需要修改这些参数
    generate_report(
        search_keywords="pancreatic cancer",  # 测试使用英文关键词
        first_post_date='2025-01-01',  # 过滤2025年1月1日之后的试验
        days_back=30,  # 向前查找30天
        phases=None,  # 包含所有阶段
        status=None,  # 包含所有状态
        location=None,  # 不限制地理位置
        use_api=True  # 直接调用API获取最新数据
    )