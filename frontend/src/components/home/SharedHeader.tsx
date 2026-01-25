import React from 'react';
import { Typography } from 'antd';
import { useNavigate } from'react-router-dom';

const { Title } = Typography;

interface SharedHeaderProps {
  title: string;
  rightContent?: React.ReactNode; // 允许传入自定义的右侧内容 (例如：返回按钮)
}

const SharedHeader: React.FC<SharedHeaderProps> = ({ title, rightContent }) => {
  const navigate = useNavigate();
  return (
    <div style={{
      height: '80px',
      background: '#1a4d33',
      boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
      display: 'flex',
      alignItems: 'center',
      paddingLeft: '32px',
      paddingRight: '32px',
      position: 'sticky',
      top: 0,
      zIndex: 100
    }}>
      <div style={{ display: 'flex', alignItems: 'center', flex: 1 }}>
        <img
          // src="/SJTU.png"
          src="/222.png"
          alt="Logo"
          onClick={() => navigate('/')}
          style={{
            height: '48px',
            width: 'auto',
            marginRight: '16px',
            cursor: 'pointer',
            transition: 'transform 0.2s ease',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.transform = 'scale(1.05)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.transform = 'scale(1)';
          }}
        />

      </div>

      {/* 渲染传入的右侧内容 */}
      {rightContent}
    </div>
  );
};

export default SharedHeader;