import React, { useEffect, useState } from 'react';
import { Card, Table, Button, Tag, message, Modal, Form, Input, Select, Space, Typography, Avatar, Descriptions, Divider, List, Popconfirm, Tabs } from 'antd';
import { CheckCircleOutlined, CloseCircleOutlined, EyeOutlined, DeleteOutlined, UserOutlined, BookOutlined, ClockCircleOutlined, PlayCircleOutlined, LinkOutlined, SearchOutlined, SyncOutlined } from '@ant-design/icons';
import { CourseResponse, CourseSharingApplication, CourseReviewRequest } from '@/types/api';
import * as admin from '@/api/admin';
import { useNavigate } from 'react-router-dom';

const { Title, Text, Paragraph } = Typography;
const { TextArea } = Input;
const { Option } = Select;
const { Search } = Input;
const { TabPane } = Tabs;

interface CourseWithUser extends CourseResponse {
  user?: {
    username: string;
    email: string;
  };
}

interface ApplicationWithUser extends CourseSharingApplication {
  user?: {
    username: string;
    email: string;
  };
}

const AdminCourseManagement: React.FC = () => {
  const navigate = useNavigate();

  // 课程管理相关状态
  const [courses, setCourses] = useState<CourseWithUser[]>([]);
  const [coursesLoading, setCoursesLoading] = useState(false);
  const [detailModalVisible, setDetailModalVisible] = useState(false);
  const [selectedCourse, setSelectedCourse] = useState<CourseWithUser | null>(null);
  const [searchText, setSearchText] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [coursesPagination, setCoursesPagination] = useState({
    current: 1,
    pageSize: 10,
    total: 0,
  });

  // 课程审核相关状态
  const [applications, setApplications] = useState<ApplicationWithUser[]>([]);
  const [applicationsLoading, setApplicationsLoading] = useState(false);
  const [reviewModalVisible, setReviewModalVisible] = useState(false);
  const [detailApplicationModalVisible, setDetailApplicationModalVisible] = useState(false);
  const [selectedApplication, setSelectedApplication] = useState<ApplicationWithUser | null>(null);
  const [reviewForm] = Form.useForm();

  // 加载课程列表
  const loadCourses = async (page = coursesPagination.current, size = coursesPagination.pageSize) => {
    setCoursesLoading(true);
    try {
      const params: any = {
        page,
        size,
      };

      if (searchText.trim()) {
        params.search = searchText.trim();
      }

      if (statusFilter !== 'all') {
        params.status = statusFilter;
      }

      const response = await admin.apiAdminGetAllCourses(params.page, params.size, params.search, params.status);
      if (response.success && response.data?.items) {
        setCourses(response.data.items);
        setCoursesPagination({
          ...coursesPagination,
          current: page,
          pageSize: size,
          total: response.data.total,
        });
      }
    } catch (error) {
      message.error('加载课程列表失败');
    } finally {
      setCoursesLoading(false);
    }
  };

  // 加载申请列表
  const loadApplications = async () => {
    setApplicationsLoading(true);
    try {
      const response = await admin.apiAdminGetCourseApplications();
      if (response.success && response.data?.items) {
        setApplications(response.data.items);
      }
    } catch (error) {
      message.error('加载申请列表失败');
    } finally {
      setApplicationsLoading(false);
    }
  };

  useEffect(() => {
    loadCourses();
    loadApplications();
  }, []);

  // 课程管理相关函数
  const handleSearch = (value: string) => {
    setSearchText(value);
    loadCourses(1);
  };

  const handleStatusFilter = (value: string) => {
    setStatusFilter(value);
    loadCourses(1);
  };

  const handleToggleStatus = async (courseId: string, currentStatus: boolean) => {
    try {
      const response = await admin.apiAdminUpdateCourseStatus(courseId, !currentStatus);
      if (response.success) {
        message.success(`课程已${!currentStatus ? '上架' : '下架'}`);
        loadCourses();
      } else {
        message.error(response.message || '操作失败');
      }
    } catch (error) {
      message.error('操作失败');
    }
  };

  const handleDeleteCourse = async (courseId: string) => {
    try {
      const response = await admin.apiAdminDeleteCourseHard(courseId);
      if (response.success) {
        message.success('课程已删除');
        loadCourses();
      } else {
        message.error(response.message || '删除失败');
      }
    } catch (error) {
      message.error('删除失败');
    }
  };

  const showCourseDetailModal = (course: CourseWithUser) => {
    setSelectedCourse(course);
    setDetailModalVisible(true);
  };

  const viewCourseDetail = (courseId: string) => {
    navigate(`/course/${courseId}`);
  };

  const getStatusTag = (isActive: boolean) => {
    return isActive ? (
      <Tag icon={<CheckCircleOutlined />} color="success">已上架</Tag>
    ) : (
      <Tag icon={<CloseCircleOutlined />} color="error">已下架</Tag>
    );
  };

  // 课程审核相关函数
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
        if (status === 'approved') {
          loadCourses(); // 审核通过后刷新课程列表
        }
      } else {
        message.error(response.message || '审核失败');
      }
    } catch (error) {
      message.error('审核失败');
    }
  };

  const showReviewModal = (application: ApplicationWithUser) => {
    setSelectedApplication(application);
    setReviewModalVisible(true);
    reviewForm.resetFields();
  };

  const showApplicationDetailModal = (application: ApplicationWithUser) => {
    setSelectedApplication(application);
    setDetailApplicationModalVisible(true);
  };

  const viewVideo = (jobId: string) => {
    navigate('/generate', {
      state: {
        showCompletedPage: true,
        jobId: jobId
      }
    });
  };

  const getApplicationStatusTag = (status: string) => {
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

  // 课程管理表格列
  const coursesColumns = [
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
      title: '教师',
      dataIndex: 'teacher_name',
      key: 'teacher_name',
      render: (teacherName: string, record: CourseWithUser) => (
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
      render: (university: string, record: CourseWithUser) => (
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
      title: '创建时间',
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
      dataIndex: 'is_active',
      key: 'is_active',
      render: (isActive: boolean) => getStatusTag(isActive),
    },
    {
      title: '操作',
      key: 'action',
      render: (_: any, record: CourseWithUser) => (
        <Space>
          <Button
            type="link"
            icon={<EyeOutlined />}
            onClick={() => showCourseDetailModal(record)}
          >
            详情
          </Button>
          <Button
            type={record.is_active ? "default" : "primary"}
            onClick={() => handleToggleStatus(record.id, record.is_active)}
          >
            {record.is_active ? '下架' : '上架'}
          </Button>
          <Popconfirm
            title="确定要删除这个课程吗？"
            description="此操作不可恢复，课程将被永久删除。"
            onConfirm={() => handleDeleteCourse(record.id)}
            okText="确定"
            cancelText="取消"
          >
            <Button danger icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  // 课程审核表格列
  const applicationsColumns = [
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
      render: (status: string) => getApplicationStatusTag(status),
    },
    {
      title: '操作',
      key: 'action',
      render: (_: any, record: ApplicationWithUser) => (
        <Space>
          <Button
            type="link"
            icon={<EyeOutlined />}
            onClick={() => showApplicationDetailModal(record)}
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
        <Title level={2} style={{ marginBottom: '24px' }}>课程管理中心</Title>

        <Tabs defaultActiveKey="courses" type="card">
          <TabPane tab="已发布课程管理" key="courses">
            <div style={{ marginBottom: '16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Space>
                <Select
                  value={statusFilter}
                  onChange={handleStatusFilter}
                  style={{ width: 120 }}
                >
                  <Option value="all">全部状态</Option>
                  <Option value="active">已上架</Option>
                  <Option value="inactive">已下架</Option>
                </Select>
                <Search
                  placeholder="搜索课程标题、教师或描述"
                  onSearch={handleSearch}
                  style={{ width: 300 }}
                  allowClear
                />
              </Space>
            </div>

            <Table
              columns={coursesColumns}
              dataSource={courses}
              loading={coursesLoading}
              rowKey="id"
              pagination={{
                ...coursesPagination,
                showSizeChanger: true,
                showQuickJumper: true,
                showTotal: (total, range) => `共 ${total} 条记录，显示 ${range[0]}-${range[1]} 条`,
                onChange: (page, size) => loadCourses(page, size),
                onShowSizeChange: (current, size) => loadCourses(1, size),
              }}
            />
          </TabPane>

          <TabPane tab="课程审核" key="review">
            <Table
              columns={applicationsColumns}
              dataSource={applications}
              loading={applicationsLoading}
              rowKey="id"
              pagination={{
                showSizeChanger: true,
                showQuickJumper: true,
                showTotal: (total, range) => `共 ${total} 条记录，显示 ${range[0]}-${range[1]} 条`,
              }}
            />
          </TabPane>
        </Tabs>
      </Card>

      {/* 课程详情模态框 */}
      <Modal
        title="课程详情"
        open={detailModalVisible}
        onCancel={() => setDetailModalVisible(false)}
        footer={[
          <Button key="view" type="primary" onClick={() => selectedCourse && viewCourseDetail(selectedCourse.id)}>
            查看课程
          </Button>,
          <Button key="close" onClick={() => setDetailModalVisible(false)}>
            关闭
          </Button>
        ]}
        width={800}
      >
        {selectedCourse && (
          <div>
            <Descriptions title="基本信息" bordered column={2}>
              <Descriptions.Item label="课程标题">{selectedCourse.title}</Descriptions.Item>
              <Descriptions.Item label="教师姓名">{selectedCourse.teacher_name}</Descriptions.Item>
              <Descriptions.Item label="学校">{selectedCourse.university}</Descriptions.Item>
              <Descriptions.Item label="学院">{selectedCourse.college}</Descriptions.Item>
              <Descriptions.Item label="分类">{selectedCourse.category}</Descriptions.Item>
              <Descriptions.Item label="状态">{getStatusTag(selectedCourse.is_active)}</Descriptions.Item>
              <Descriptions.Item label="创建者ID">{selectedCourse.user_id}</Descriptions.Item>
              <Descriptions.Item label="创建时间">
                {new Date(selectedCourse.created_at).toLocaleString()}
              </Descriptions.Item>
            </Descriptions>

            <Divider />

            <div>
              <Text strong>课程描述：</Text>
              <div style={{ marginTop: '8px', padding: '12px', background: '#f5f5f5', borderRadius: '4px' }}>
                {selectedCourse.description}
              </div>
            </div>

            <Divider />

            <div>
              <Text strong>视频数量：</Text>
              <Text style={{ marginLeft: '8px' }}>
                {selectedCourse.videos?.length || 0} 个视频
              </Text>
            </div>
          </div>
        )}
      </Modal>

      {/* 课程审核模态框 */}
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

            <div>
              <Text strong>课程章节：</Text>
              {selectedApplication.video_ids && selectedApplication.video_ids.length > 0 ? (
                <List
                  style={{ marginTop: '12px' }}
                  dataSource={selectedApplication.video_ids}
                  renderItem={(video: any, index: number) => (
                    <List.Item
                      style={{
                        padding: '8px 12px',
                        border: '1px solid #f0f0f0',
                        borderRadius: '4px',
                        marginBottom: '6px'
                      }}
                      actions={[
                        <Button
                          key="view"
                          type="link"
                          icon={<LinkOutlined />}
                          onClick={() => viewVideo(video.job_id)}
                          size="small"
                        >
                          查看
                        </Button>
                      ]}
                    >
                      <div style={{ display: 'flex', alignItems: 'center' }}>
                        <span style={{ marginRight: '12px', color: '#1890ff', fontWeight: 'bold' }}>
                          {index + 1}.
                        </span>
                        <div>
                          <Text strong style={{ fontSize: '14px' }}>{video.title}</Text>
                          <br />
                          <Text type="secondary" style={{ fontSize: '12px' }}>
                            Job ID: {video.job_id}
                          </Text>
                        </div>
                      </div>
                    </List.Item>
                  )}
                />
              ) : (
                <div style={{ textAlign: 'center', padding: '16px', color: '#999', fontSize: '14px' }}>
                  暂无章节信息
                </div>
              )}
            </div>

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

      {/* 申请详情模态框 */}
      <Modal
        title="申请详情"
        open={detailApplicationModalVisible}
        onCancel={() => setDetailApplicationModalVisible(false)}
        footer={[
          <Button key="close" onClick={() => setDetailApplicationModalVisible(false)}>
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
              <Descriptions.Item label="状态">{getApplicationStatusTag(selectedApplication.status)}</Descriptions.Item>
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

            <Divider />

            <div>
              <Text strong>课程章节：</Text>
              {selectedApplication.video_ids && selectedApplication.video_ids.length > 0 ? (
                <List
                  style={{ marginTop: '12px' }}
                  dataSource={selectedApplication.video_ids}
                  renderItem={(video: any, index: number) => (
                    <List.Item
                      style={{
                        padding: '12px',
                        border: '1px solid #f0f0f0',
                        borderRadius: '6px',
                        marginBottom: '8px'
                      }}
                      actions={[
                        <Button
                          key="view"
                          type="link"
                          icon={<PlayCircleOutlined />}
                          onClick={() => viewVideo(video.job_id)}
                          size="small"
                        >
                          查看视频
                        </Button>
                      ]}
                    >
                      <List.Item.Meta
                        avatar={
                          <div style={{
                            width: '32px',
                            height: '32px',
                            borderRadius: '50%',
                            background: '#1890ff',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            color: 'white',
                            fontWeight: 'bold'
                          }}>
                            {index + 1}
                          </div>
                        }
                        title={
                          <div>
                            <Text strong>{video.title}</Text>
                            <Text type="secondary" style={{ fontSize: '12px', marginLeft: '8px' }}>
                              Job ID: {video.job_id}
                            </Text>
                          </div>
                        }
                        description={
                          video.description && (
                            <Text type="secondary" style={{ fontSize: '14px' }}>
                              {video.description}
                            </Text>
                          )
                        }
                      />
                    </List.Item>
                  )}
                />
              ) : (
                <div style={{ textAlign: 'center', padding: '20px', color: '#999' }}>
                  <BookOutlined style={{ fontSize: '24px', marginBottom: '8px' }} />
                  <div>暂无章节信息</div>
                </div>
              )}
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

export default AdminCourseManagement;