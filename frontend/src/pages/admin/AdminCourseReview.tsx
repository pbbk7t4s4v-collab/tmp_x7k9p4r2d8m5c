import React, { useEffect, useState } from 'react';
import { Card, Table, Button, Tag, message, Modal, Form, Input, Select, Space, Typography, Avatar, Descriptions, Divider } from 'antd';
import { CheckCircleOutlined, CloseCircleOutlined, EyeOutlined, UserOutlined, BookOutlined, ClockCircleOutlined } from '@ant-design/icons';
import { CourseSharingApplication, CourseReviewRequest } from '@/types/api';
import * as admin from '@/api/admin';

const { Title, Text, Paragraph } = Typography;
const { TextArea } = Input;
const { Option } = Select;

interface ApplicationWithUser extends CourseSharingApplication {
  user?: {
    username: string;
    email: string;
  };
}

const AdminCourseReview: React.FC = () => {
  const [applications, setApplications] = useState<ApplicationWithUser[]>([]);
  const [loading, setLoading] = useState(false);
  const [reviewModalVisible, setReviewModalVisible] = useState(false);
  const [detailModalVisible, setDetailModalVisible] = useState(false);
  const [selectedApplication, setSelectedApplication] = useState<ApplicationWithUser | null>(null);
  const [reviewForm] = Form.useForm();

  // 加载申请列表
  const loadApplications = async () => {
    setLoading(true);
    try {
      const response = await admin.apiAdminGetCourseApplications();
      if (response.success && response.data?.items) {
        setApplications(response.data.items);
      }
    } catch (error) {
      message.error('加载申请列表失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadApplications();
  }, []);

  // 审核申请
  const handleReview = async (applicationId: string, status: 'approved' | 'rejected') => {
    try {
      const values = await reviewForm.validateFields();
      const reviewData: CourseReviewRequest = {
        status,
        comment: values.comment || ''
      };

      const response = await admin.apiAdminReviewCourseApplication(applicationId, reviewData);
      if (response.success) {
        message.success(`${status === 'approved' ? '通过' : '拒绝'}审核成功`);
        setReviewModalVisible(false);
        reviewForm.resetFields();
        loadApplications();
      } else {
        message.error(response.message || '审核失败');
      }
    } catch (error) {
      message.error('审核失败');
    }
  };

  // 显示审核模态框
  const showReviewModal = (application: ApplicationWithUser) => {
    setSelectedApplication(application);
    setReviewModalVisible(true);
    reviewForm.resetFields();
  };

  // 显示详情模态框
  const showDetailModal = (application: ApplicationWithUser) => {
    setSelectedApplication(application);
    setDetailModalVisible(true);
  };

  // 获取状态标签
  const getStatusTag = (status: string) => {
    switch (status) {
      case 'pending':
        return <Tag icon={<ClockCircleOutlined />} color="processing">待审核</Tag>;
      case 'approved':
        return <Tag icon={<CheckCircleOutlined />} color="success">已通过</Tag>;
      case 'rejected':
        return <Tag icon={<CloseCircleOutlined />} color="error">已拒绝</Tag>;
      default:
        return <Tag>未知状态</Tag>;
    }
  };

  // 表格列配置
  const columns = [
    {
      title: '课程标题',
      dataIndex: 'title',
      key: 'title',
      ellipsis: true,
      render: (title: string) => (
        <div style={{ display: 'flex', alignItems: 'center' }}>
          <BookOutlined style={{ marginRight: '8px', color: '#1890ff' }} />
          <Text strong>{title}</Text>
        </div>
      ),
    },
    {
      title: '申请人',
      dataIndex: 'user_id',
      key: 'user_id',
      render: (userId: string) => (
        <Text>{userId}</Text> // 暂时显示ID，后续可以扩展为用户名
      ),
    },
    {
      title: '教师',
      dataIndex: 'teacher_name',
      key: 'teacher_name',
      render: (teacherName: string, record: ApplicationWithUser) => (
        <div style={{ display: 'flex', alignItems: 'center' }}>
          <Avatar
            src={record.teacher_avatar_url}
            icon={<UserOutlined />}
            size={24}
            style={{ marginRight: '8px' }}
          />
          <Text>{teacherName}</Text>
        </div>
      ),
    },
    {
      title: '学校',
      dataIndex: 'university',
      key: 'university',
      render: (university: string, record: ApplicationWithUser) => (
        <div>
          <Text>{university}</Text>
          <br />
          <Text type="secondary" style={{ fontSize: '12px' }}>
            {record.college}
          </Text>
        </div>
      ),
    },
    {
      title: '分类',
      dataIndex: 'category',
      key: 'category',
      render: (category: string) => <Tag>{category}</Tag>,
    },
    {
      title: '申请时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (createdAt: string) => (
        <Text type="secondary">
          {new Date(createdAt).toLocaleString()}
        </Text>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => getStatusTag(status),
    },
    {
      title: '操作',
      key: 'action',
      render: (_: any, record: ApplicationWithUser) => (
        <Space>
          <Button
            type="link"
            icon={<EyeOutlined />}
            onClick={() => showDetailModal(record)}
          >
            查看详情
          </Button>
          {record.status === 'pending' && (
            <>
              <Button
                type="primary"
                size="small"
                onClick={() => showReviewModal(record)}
              >
                审核
              </Button>
            </>
          )}
        </Space>
      ),
    },
  ];

  return (
    <div style={{ padding: '24px' }}>

      <Card>
        <Table
          columns={columns}
          dataSource={applications}
          loading={loading}
          rowKey="id"
          pagination={{
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total, range) => `共 ${total} 条记录，显示 ${range[0]}-${range[1]} 条`,
          }}
        />
      </Card>

      {/* 审核模态框 */}
      <Modal
        title="审核课程分享申请"
        open={reviewModalVisible}
        onCancel={() => setReviewModalVisible(false)}
        footer={null}
        width={600}
      >
        {selectedApplication && (
          <div>
            <Descriptions title="课程信息" bordered column={2}>
              <Descriptions.Item label="课程标题">{selectedApplication.title}</Descriptions.Item>
              <Descriptions.Item label="教师姓名">{selectedApplication.teacher_name}</Descriptions.Item>
              <Descriptions.Item label="学校">{selectedApplication.university}</Descriptions.Item>
              <Descriptions.Item label="学院">{selectedApplication.college}</Descriptions.Item>
              <Descriptions.Item label="分类">{selectedApplication.category}</Descriptions.Item>
              <Descriptions.Item label="申请时间">
                {new Date(selectedApplication.created_at).toLocaleString()}
              </Descriptions.Item>
            </Descriptions>

            <Divider />

            <Paragraph>
              <Text strong>课程描述：</Text>
              <br />
              {selectedApplication.description}
            </Paragraph>

            <Divider />

            <Form form={reviewForm} layout="vertical">
              <Form.Item name="comment" label="审核意见">
                <TextArea
                  rows={4}
                  placeholder="请输入审核意见（可选）"
                />
              </Form.Item>

              <Form.Item>
                <Space>
                  <Button
                    type="primary"
                    onClick={() => handleReview(selectedApplication.id, 'approved')}
                  >
                    通过审核
                  </Button>
                  <Button
                    danger
                    onClick={() => handleReview(selectedApplication.id, 'rejected')}
                  >
                    拒绝申请
                  </Button>
                  <Button onClick={() => setReviewModalVisible(false)}>
                    取消
                  </Button>
                </Space>
              </Form.Item>
            </Form>
          </div>
        )}
      </Modal>

      {/* 详情模态框 */}
      <Modal
        title="申请详情"
        open={detailModalVisible}
        onCancel={() => setDetailModalVisible(false)}
        footer={[
          <Button key="close" onClick={() => setDetailModalVisible(false)}>
            关闭
          </Button>
        ]}
        width={700}
      >
        {selectedApplication && (
          <div>
            <Descriptions title="基本信息" bordered column={2}>
              <Descriptions.Item label="课程标题">{selectedApplication.title}</Descriptions.Item>
              <Descriptions.Item label="教师姓名">{selectedApplication.teacher_name}</Descriptions.Item>
              <Descriptions.Item label="学校">{selectedApplication.university}</Descriptions.Item>
              <Descriptions.Item label="学院">{selectedApplication.college}</Descriptions.Item>
              <Descriptions.Item label="分类">{selectedApplication.category}</Descriptions.Item>
              <Descriptions.Item label="状态">{getStatusTag(selectedApplication.status)}</Descriptions.Item>
              <Descriptions.Item label="申请人ID">{selectedApplication.user_id}</Descriptions.Item>
              <Descriptions.Item label="申请时间">
                {new Date(selectedApplication.created_at).toLocaleString()}
              </Descriptions.Item>
            </Descriptions>

            <Divider />

            <div>
              <Text strong>课程描述：</Text>
              <Paragraph style={{ marginTop: '8px' }}>
                {selectedApplication.description}
              </Paragraph>
            </div>

            {selectedApplication.review_comment && (
              <div style={{ marginTop: '16px' }}>
                <Text strong>审核意见：</Text>
                <Paragraph style={{ marginTop: '8px', color: selectedApplication.status === 'rejected' ? '#ff4d4f' : '#52c41a' }}>
                  {selectedApplication.review_comment}
                </Paragraph>
              </div>
            )}

            {selectedApplication.reviewed_at && (
              <div style={{ marginTop: '16px' }}>
                <Text strong>审核时间：</Text>
                <Text style={{ marginLeft: '8px' }}>
                  {new Date(selectedApplication.reviewed_at).toLocaleString()}
                </Text>
              </div>
            )}
          </div>
        )}
      </Modal>
    </div>
  );
};

export default AdminCourseReview;
