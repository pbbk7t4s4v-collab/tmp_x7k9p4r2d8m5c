// src/components/home/HomeHeader.tsx

import React from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { Button, Tooltip } from 'antd';
import { QuestionCircleOutlined,BookOutlined } from '@ant-design/icons';

// 炫酷的语言切换器组件
const LanguageSwitcher: React.FC = () => {
  const { i18n } = useTranslation();
  
  // 判断当前是否是中文环境（'zh', 'zh-CN' 等）
  const isChinese = i18n.language.startsWith('zh');

  const toggleLanguage = () => {
    const nextLanguage = isChinese ? 'en' : 'zh';
    i18n.changeLanguage(nextLanguage);
  };

  return (
    <>
      {/* CSS 样式 - 直接内联，方便复制 */}
      <style>{`
        .lang-switcher {
          position: relative;
          display: flex;
          align-items: center;
          width: 80px;
          height: 36px;
          background-color: rgba(0, 0, 0, 0.25);
          border-radius: 18px;
          cursor: pointer;
          padding: 4px;
          box-sizing: border-box;
          border: 1px solid rgba(255, 255, 255, 0.2);
          margin-right: 24px;
        }

        .lang-slider {
          position: absolute;
          width: 38px;
          height: 26px;
          background-color: #fff;
          border-radius: 13px;
          transition: transform 0.3s cubic-bezier(0.645, 0.045, 0.355, 1);
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
        }

        .lang-slider.zh {
          transform: translateX(0px);
        }

        .lang-slider.en {
          transform: translateX(33px);
        }

        .lang-option {
          flex: 1;
          text-align: center;
          font-size: 14px;
          font-weight: 500;
          color: rgba(255, 255, 255, 0.65);
          z-index: 1;
          transition: color 0.3s ease;
          user-select: none; /* 防止文字被选中 */
        }

        .lang-option.active {
          color: #1a4d33; /* 切换后文字颜色变为深绿色 */
        }
      `}</style>

      {/* 切换器本体 */}
      <div className="lang-switcher" onClick={toggleLanguage} title="切换语言 / Switch Language">
        <div className={`lang-slider ${isChinese ? 'zh' : 'en'}`}></div>
        <span className={`lang-option ${isChinese ? 'active' : ''}`}>中</span>
        <span className={`lang-option ${!isChinese ? 'active' : ''}`}>EN</span>
      </div>
    </>
  );
};


// 你的 HomeHeader 组件
const HomeHeader = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();

  return (
    <div style={{
        height: '80px',
        background: '#1a4d33',
        boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
        position: 'sticky',
        top: 0,
        zIndex: 100,
        display: 'flex',
        alignItems: 'center',
        paddingLeft: '32px'
      }}>
      <img
        // src="/SJTU.png"
        src="/logo_white.png"
        alt="Logo"
        style={{ height: '48px', width: 'auto', marginRight: '16px' }}
      />
      
      {/* 保持文档按钮在最右边 */}
      <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center' }}>
        <Tooltip title={t('tooltips.documentation')}>
          <Button 
            type="link" 
            style={{fontSize: '24px', color: 'white', marginRight: '16px'}} 
            icon={<QuestionCircleOutlined />}
            href="https://wcna7fntvars.feishu.cn/wiki/OrrwwOYB1iyTVTkX5YWcEX0AnYe?from=from_copylink"
            target="_blank"
          />
        </Tooltip>

        {/* 在这里使用新的语言切换器 */}
        <LanguageSwitcher />
      </div>
    </div>
  );
};

export default HomeHeader;