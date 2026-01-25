import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import {
  DashboardOutlined,
  SafetyCertificateOutlined,
  SettingOutlined,
  HomeOutlined,
  UserOutlined,
  LogoutOutlined,
  ProfileOutlined,
  BarsOutlined,
  TeamOutlined,
  QuestionCircleOutlined,
  AccountBookOutlined,
  BookOutlined,
  WalletOutlined,
  ExpandOutlined,
  GiftOutlined,
  BarChartOutlined,
  AppstoreOutlined
} from '@ant-design/icons';
import { Image, Spin, Input, Form, Tag, Descriptions, Tooltip, Button, Layout, Menu, theme, Dropdown, Avatar, Space, MenuProps, notification, Modal, message } from 'antd';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import FloatingSidebar from '../FloatingSidebar';
import SharedHeader from '../home/SharedHeader';
import dayjs from 'dayjs';
import { apiMe, updateCurrentUser } from '@/api/auth';
import { formatDate } from '@/utils/time';
import ReactMarkdown from 'react-markdown';

const { Header, Sider, Content } = Layout;
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
const App: React.FC = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [user, setUser] = useState(JSON.parse(localStorage.getItem('userInfo') || '{}'));

  // 弹窗显示状态
  const [isProfileOpen, setIsProfileOpen] = useState(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);

  // 设置表单引用
  const [form] = Form.useForm();
  const [isSystemHelpVisible, setIsSystemHelpVisible] = useState(false);

  const [helpDocs, setHelpDocs] = useState({
    systemTutorial: ''
  });

  useEffect(() => {
    // 定义文件路径 (相对于 public 目录)
    const docs = [
      { key: 'systemTutorial', path: '/help_docs/system_tutorial.md' }
    ];

    const loadDocs = async () => {
      try {
        const promises = docs.map(async (doc) => {
          const res = await fetch(doc.path);
          const text = await res.text();
          return { key: doc.key, text };
        });

        const results = await Promise.all(promises);

        const newDocs: any = {};
        results.forEach((item) => {
          newDocs[item.key] = item.text;
        });

        setHelpDocs(prev => ({ ...prev, ...newDocs }));
      } catch (error) {
        console.error("加载帮助文档失败:", error);
      }
    };

    loadDocs();
  }, []);

  const MarkdownContainer = ({ content }: { content: string }) => {
    // ---- 新增状态用于控制全屏预览 ----
    const [previewVisible, setPreviewVisible] = useState(false);
    const [previewImageSrc, setPreviewImageSrc] = useState('');

    // 处理点击全屏按钮的方法
    const handleFullScreenClick = (src: string) => {
      setPreviewImageSrc(src);
      setPreviewVisible(true);
    };

    return (
      <div style={{
        color: 'rgba(0, 0, 0, 0.85)',
        lineHeight: '1.8',
        fontSize: '15px',
        fontWeight: 500,
        maxHeight: '60vh',
        overflowY: 'auto',
        padding: '0 12px',
        position: 'relative' // 为加载 Spin 提供定位基准
      }}>
        {content ? (
          <>
            <ReactMarkdown
              components={{
                // 👇👇👇 核心修改区域：自定义 img 渲染 👇👇👇
                img: ({ node, ...props }) => {
                  const src = props.src as string;
                  if (!src) return null;

                  return (
                    // 1. 外层包裹一个相对定位的容器
                    <div style={{ position: 'relative', display: 'inline-block', maxWidth: '100%', margin: '16px 0' }}>

                      {/* 2. 原始图片渲染（保持之前的样式和 referrerPolicy） */}
                      <img
                        {...props}
                        style={{
                          maxWidth: '100%',
                          height: 'auto',
                          borderRadius: '8px',
                          boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
                          display: 'block' // 消除图片底部的幽灵间距
                        }}
                        referrerPolicy="no-referrer"
                      />

                      {/* 3. 右下角的全屏按钮 */}
                      <Button
                        type="text"
                        icon={<ExpandOutlined style={{ fontSize: '16px', color: '#fff' }} />}
                        onClick={() => handleFullScreenClick(src)}
                        style={{
                          position: 'absolute', // 绝对定位
                          bottom: '8px',        // 距离底部 8px
                          right: '8px',         // 距离右侧 8px
                          // 按钮样式：做成半透明磨砂玻璃风格，与 Modal 呼应
                          backgroundColor: 'rgba(0, 0, 0, 0.10)',
                          backdropFilter: 'blur(4px)',
                          borderRadius: '6px',
                          width: '32px',
                          height: '32px',
                          display: 'flex',
                          justifyContent: 'center',
                          alignItems: 'center',
                          padding: 0,
                          zIndex: 10, // 确保在图片上方
                          cursor: 'pointer',
                          transition: 'all 0.3s',
                        }}
                        // 添加简单的 hover 效果 (可选，需要 CSS-in-JS 或 class 支持，这里简单演示行内样式局限性)
                        onMouseEnter={(e) => e.currentTarget.style.backgroundColor = 'rgba(0, 0, 0, 0.50)'}
                        onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'rgba(0, 0, 0, 0.10)'}
                      />
                    </div>
                  );
                },
              }}
            >
              {content}
            </ReactMarkdown>

            {/* 👇👇👇 4. 放置一个隐藏的 AntD Image 组件用于接管全屏预览 👇👇👇 */}
            <Image
              width={0}
              height={0}
              src={previewImageSrc} // 设置当前要预览的图片地址
              style={{ display: 'none' }} // 隐藏占位符
              preview={{
                visible: previewVisible,
                onVisibleChange: (visible) => setPreviewVisible(visible),
                // 关键：确保预览大图时也带有 no-referrer，否则 Gitee 大图也看不了
                imageRender: (originalNode) => React.cloneElement(originalNode, { referrerPolicy: 'no-referrer' })
              }}
            />
          </>
        ) : (
          <Spin tip="加载文档中..." style={{ display: 'flex', justifyContent: 'center', padding: '40px' }} />
        )}
      </div>
    );
  };

  // 处理设置保存
  const handleSettingsSave = () => {
    form.validateFields().then(async (values) => {
      // 模拟API请求更新数据
      const response = await updateCurrentUser(values);
      if (!response.success) {
        message.error('个人信息更新失败！');
        return;
      }
      message.success('个人信息更新成功！');
      const res = await apiMe(); // 更新用户信息
      setUser(res.data)
      localStorage.setItem('userInfo', JSON.stringify(user));
      setIsSettingsOpen(false);
    }).catch(info => {
      console.log('Validate Failed:', info);
    });
  };

  useEffect(() => {
    localStorage.removeItem('attachment_dir_id');
  }, []);
  const menuItems = [
    {
      key: '/',
      icon: <HomeOutlined />,
      label: t('menu.home'),
    },
    {
      key: '/dashboard',
      icon: <DashboardOutlined />,
      label: t('menu.dashboard'),
    },
    {
      key: '/courses',
      icon: <svg
            style={{width: '20px', height: '20px',marginLeft: '-2px'}}
              viewBox="0 0 1024 1024"
              version="1.1" 
              xmlns="http://www.w3.org/2000/svg" 
              p-id="22750" width="48" height="48">
                <path d="M859.976 69.113H166.141c-13.788 0-25.352 11.119-25.352 25.352v839.273c0 13.788 11.119 25.352 25.352 25.352h693.835c13.789 0 25.352-11.119 25.352-25.352V94.465c0-14.233-11.564-25.352-25.352-25.352zM681.625 614.841h-59.154V464.51H548.64v150.331h-29.354V464.51h-73.387v150.331h-36.47V464.51H348.94v150.331h-26.686V464.51h-69.383v150.331h-61.378V391.124H835.07v223.717H726.101l18.681-8.895-67.16-141.436-54.706 25.797 58.709 124.534z m105.854-285.095l47.59-114.75v114.75h-47.59z m47.59-210.374v81.836l-51.148-20.903-59.599 144.549 12.008 4.893H631.812V173.189H557.98v156.557h-27.576V173.189h-73.831v156.557H425.44V173.189h-78.278v156.557h-34.248V173.189h-60.488v156.557h-61.377V119.372h644.02zM191.048 676.219h643.576v99.183l-48.479-21.794-64.046 142.77 26.241 12.009H618.023V759.391h-60.487v148.996h-38.25V759.391h-73.387v148.996h-40.918V759.391h-60.488v148.996h-35.581V759.391h-60.488v148.996h-57.375V676.219h-0.001z m591.984 232.168l51.593-115.194v115.194h-51.593z" p-id="22751" fill="#ffffff"></path></svg>,
      label: t('menu.courses'),
    },
    {
      key: '/tcoin',
      icon:<svg 
            style={{width: '20px', height: '20px',marginLeft: '-2px'}}
            viewBox="0 0 1024 1024" version="1.1" xmlns="http://www.w3.org/2000/svg" p-id="10756" width="200" height="200"><path d="M892 330c4.4 0 8 3.6 8 8v482c0 4.4-3.6 8-8 8H132c-4.4 0-8-3.6-8-8V338c0-4.4 3.6-8 8-8h760m0-60H132c-37.6 0-68 30.4-68 68v482c0 37.6 30.4 68 68 68h760c37.6 0 68-30.4 68-68V338c0-37.6-30.4-68-68-68z" p-id="10757" fill="#ffffff"></path><path d="M203 270l15.7-74.2c0.9-4.2 4.6-6.4 7.8-6.4 0.6 0 1.1 0.1 1.7 0.2L608.4 270H892c3.4 0 6.7 0.3 9.9 0.7L240.6 130.9c-4.7-1-9.5-1.5-14.1-1.5-31.5 0-59.7 22-66.5 54L141.7 270H203zM899.3 508.2v122.5h-202c-33.8 0-61.3-27.5-61.3-61.3s27.5-61.3 61.3-61.3h202m60-59.9h-262c-67 0-121.3 54.3-121.3 121.3s54.3 121.3 121.3 121.3h262V448.2z" p-id="10758" fill="#ffffff"></path><path d="M710.8 534.9c-19.1 0-34.6 15.5-34.6 34.6s15.5 34.6 34.6 34.6 34.6-15.5 34.6-34.6-15.5-34.6-34.6-34.6z" p-id="10759" fill="#ffffff"></path></svg>,
      label: t('menu.tcoin'),
    },
    {
      key: '/my-courses',
      icon: <BarChartOutlined />,
      label: t('menu.myCourseStatus'),
    },
  ];

  // 2. 如果是管理员，添加嵌套的管理菜单
  if (user.is_superuser) {
    menuItems.push({
      key: 'admin',
      icon: <SafetyCertificateOutlined />,
      label: t('menu.admin'),
      children: [
        {
          key: '/admin/users',
          icon: <TeamOutlined />,
          label: t('menu.users'),
        },
        {
          key: '/admin/jobs',
          icon: <BarsOutlined />,
          label: t('menu.jobs'),
        },
        {
          key: '/admin/package',
          icon: <AccountBookOutlined />,
          label: t('menu.package'),
        },
        {
          key: '/admin/wallets',
          icon: <WalletOutlined />,
          label: t('menu.wallets'),
        },
        {
          key: '/admin/redeem-codes',
          icon: <GiftOutlined />,
          label: t('menu.redeemCodes'),
        },
        {
          key: '/admin/course-management',
          icon: <AppstoreOutlined />,
          label: t('menu.courseManagement'),
        },
      ]
    } as any);
  }

  const userMenuItems: MenuProps['items'] = [
    {
      key: 'profile',
      icon: <ProfileOutlined />,
      label: t('menu.profile'),
    },
    {
      key: 'settings',
      icon: <SettingOutlined />,
      label: t('menu.settings'),
    },
    {
      type: 'divider',
    },
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: t('menu.logout'),
      danger: true,
    },
  ];
  const handleUserMenuClick: MenuProps['onClick'] = ({ key }) => {
    switch (key) {
      case 'logout':

        // 询问是否退出登录
        Modal.confirm({
          title: t('personalSettings.confirmLogout'),
          content: t('personalSettings.logoutContent'),
          okText: t('personalSettings.confirm'),
          cancelText: t('personalSettings.cancel'),
          onOk() {
            // 执行退出逻辑
            localStorage.removeItem('access_token');
            localStorage.removeItem('userInfo');
            message.success(t('personalSettings.logoutSuccess'));
            navigate('/login'); // 跳转到登录页
          },
          onCancel() {
            // 用户取消，不做任何操作
          },
        });
        break;
      case 'settings':// 打开设置时，回填表单数据
        form.setFieldsValue({
          username: user.username,
          full_name: user.full_name,
          email: user.email
        });
        setIsSettingsOpen(true);
        break;

      case 'profile':
        setIsProfileOpen(true);
        break;
      default:
        break;
    }
  };
  return (
    <Layout>
      <FloatingSidebar menuItems={menuItems} />
      <Modal
        title="个人资料"
        open={isProfileOpen}
        onCancel={() => setIsProfileOpen(false)}
        footer={[
          <Button key="close" onClick={() => setIsProfileOpen(false)}>
            关闭
          </Button>
        ]}
        width={600}
      >
        <div style={{ display: 'flex', justifyContent: 'center', marginBottom: 24, marginTop: 10 }}>
          <Avatar size={64} style={{ backgroundColor: '#1890ff' }}>
            {user.full_name?.[0]?.toUpperCase()}
          </Avatar>
        </div>

        <Descriptions bordered column={1} size="middle">
          <Descriptions.Item label="用户 ID">
            <span style={{ fontSize: 12, color: '#999' }}>{user.id}</span>
          </Descriptions.Item>
          <Descriptions.Item label="用户名">{user.username}</Descriptions.Item>
          <Descriptions.Item label="全名">{user.full_name}</Descriptions.Item>
          <Descriptions.Item label="邮箱">{user.email}</Descriptions.Item>
          <Descriptions.Item label="账号状态">
            <Space>
              {user.is_active ? <Tag color="success">激活</Tag> : <Tag color="error">冻结</Tag>}
              {user.is_superuser && <Tag color="gold">超级管理员</Tag>}
            </Space>
          </Descriptions.Item>
          <Descriptions.Item label="注册时间">
            {/* {dayjs(user.created_at).format('YYYY年MM月DD日 HH:mm:ss')} */}
            {formatDate(user.created_at, 'YYYY年MM月DD日 HH:mm:ss')}
          </Descriptions.Item>
        </Descriptions>
      </Modal>

      {/* 2. Settings Modal (设置弹窗) */}
      <Modal
        title={t("personalSettings.accountSettings")}
        open={isSettingsOpen}
        onOk={handleSettingsSave}
        onCancel={() => setIsSettingsOpen(false)}
        okText={t("personalSettings.saveChanges")}
        cancelText={t("personalSettings.cancel")}
      >
        <Form
          form={form}
          layout="vertical"
          name="user_settings"
          initialValues={{
            username: user.username,
            full_name: user.full_name,
            email: user.email
          }}
        >
          <Form.Item
            name="username"
            label={t("personalSettings.username")}
            rules={[{ required: true, message: t("personalSettings.enterUsername") }]}
          >
            <Input disabled placeholder={t("personalSettings.usernameDisabledHint")} />
          </Form.Item>

          <Form.Item
            name="full_name"
            label={t("personalSettings.fullName")}
            rules={[{ required: true, message: t("personalSettings.enterFullName") }]}
          >
            <Input placeholder={t("personalSettings.enterFullName")} />
          </Form.Item>

          <Form.Item
            name="email"
            label={t("personalSettings.email")}
            rules={[
              { required: true, message: t("personalSettings.enterEmail") },
              { type: 'email', message: t("personalSettings.invalidEmail") }
            ]}
          >
            <Input placeholder="example@outlook.com" />
          </Form.Item>

          {/* 这里可以根据需要添加密码修改等字段 */}
        </Form>
      </Modal>
      {/* <Modal
        title="TeachMaster使用手册"
        open={isSystemHelpVisible}
        onCancel={() => setIsSystemHelpVisible(false)}
        footer={null}
        width={1200}
        styles={{ body: { padding: '20px' } }}
      >
        <MarkdownContainer content={helpDocs.systemTutorial} />
      </Modal> */}
      <Modal
        title={
          <div style={{
            fontSize: '24px',
            fontWeight: 'bold',
            color: '#1f1f1f',
            paddingBottom: '8px'
          }}>
            {t("menu.manualTitle")}
          </div>
        }
        open={isSystemHelpVisible}
        onCancel={() => setIsSystemHelpVisible(false)}
        footer={null}
        width={1000}
        centered // 建议加上，居中显示效果更好
        // 👇 重点修改这里：使用 styles 属性配置磨砂效果
        styles={{
          mask: {
            backdropFilter: 'blur(4px)', // 背景遮罩也加一点模糊，更显高级
            WebkitBackdropFilter: 'blur(4px)', // 兼容 Safari
          },
          content: {
            backgroundColor: 'rgba(255, 255, 255, 0.75)', // 背景颜色必须半透明，不能是纯白
            backdropFilter: 'blur(20px) saturate(180%)', // 磨砂核心：模糊 + 增加饱和度防止灰暗
            WebkitBackdropFilter: 'blur(20px) saturate(180%)', // 兼容 Safari
            border: '1px solid rgba(255, 255, 255, 0.3)', // 玻璃边缘的高光边框
            boxShadow: '0 8px 32px 0 rgba(31, 38, 135, 0.15)', // 柔和的投影
            borderRadius: '16px', // 稍微加大圆角，玻璃拟态圆角大一点好看
          },
          header: {
            backgroundColor: 'transparent', // 标题栏背景透明
            marginBottom: '10px'
          },
          body: {
            padding: '20px',
            backgroundColor: 'transparent' // body 背景透明
          }
        }}
      >
        <MarkdownContainer content={helpDocs.systemTutorial} />
      </Modal>
      <Layout style={{ height: '100vh', background: 'linear-gradient(135deg, #243127 0%, #2d3c2f 25%, #1a6b52 50%, #167c60 75%, #243127 100%)' }}>
        <SharedHeader title={""} rightContent={
          <Header
            style={{
              // [修改] 增加内边距, 24px 是 antd 默认的边距
              padding: '0 24px',
              background: 'rgb(26, 77, 51)',
              // [修改] 使用 Flex 布局
              display: 'flex',
              justifyContent: 'space-between', // 两端对齐
              alignItems: 'center',

            }}
          >
            <div> </div>

            {/* --- 右侧 --- */}
            <Space>
              <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center' }}>
                <Tooltip title={t('tooltips.documentation')}>
                  <Button
                    type="text"
                    shape="circle"
                    size="small"
                    icon={<QuestionCircleOutlined />}
                    style={{ fontSize: '24px', color: 'white', marginRight: '16px' }}
                    onClick={() => setIsSystemHelpVisible(true)}
                  />
                </Tooltip>
                <LanguageSwitcher />
              </div>
              {/* 示例：未来可以添加一个通知铃铛
            <Badge count={5}>
              <Avatar shape="square" icon={<BellOutlined />} style={{ cursor: 'pointer' }} />
            </Badge>
            */}

              {/* 用户头像下拉菜单 */}
              <Dropdown
                menu={{
                  items: userMenuItems,
                  onClick: handleUserMenuClick,
                }}
                placement="bottomRight"
                arrow
              >
                <Avatar
                  style={{ backgroundColor: '#ffffffff', cursor: 'pointer', color: 'green', backdropFilter: 'blur(10px)' }}
                  icon={<UserOutlined />}
                />
              </Dropdown>
            </Space>
          </Header>
        }></SharedHeader>
        <Content
          style={{
            minHeight: 280,
            overflow: 'auto',
          }}
        >
          <div style={{
            minHeight: 360,
            // background: '#fff', 
            borderRadius: 6,
          }}>
            {/* 关键点: <Outlet /> 是一个占位符，所有子路由的组件都会在这里渲染 */}
            <Outlet />
          </div>
        </Content>
      </Layout>
    </Layout>
  );
};

export default App;