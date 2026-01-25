import React, { useState, useEffect } from 'react';
import { 
  Table, Tag, Button, Modal, Drawer, Descriptions, 
  Form, Input, Select, Space, Card, message, Popconfirm, Row, Col 
} from 'antd';
import { PlusOutlined, SearchOutlined, ReloadOutlined } from '@ant-design/icons';
import JsonView from 'react18-json-view';
import 'react18-json-view/src/style.css';
import 'react18-json-view/src/dark.css';

// 引入API
import { 
  apiAdminGetJobs, 
  apiAdminUpdateJob, 
  apiAdminDeleteJob 
} from '@/api/admin';
import { formatDate } from '@/utils/time';

const { Option } = Select;
const { TextArea } = Input;

const AdminJobs: React.FC = () => {
  // --- State 定义 ---
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [pagination, setPagination] = useState({ current: 1, pageSize: 10, total: 0 });
  
  // 详情 Drawer State
  const [detailOpen, setDetailOpen] = useState(false);
  const [currentJobDetail, setCurrentJobDetail] = useState<any>(null);

  // 新增/编辑 Modal State
  const [modalOpen, setModalOpen] = useState(false);
  const [isEditMode, setIsEditMode] = useState(false);
  const [modalLoading, setModalLoading] = useState(false);
  
  // Forms
  const [searchForm] = Form.useForm();
  const [modalForm] = Form.useForm();

  // --- 数据获取 ---
  const fetchJobs = async (page = 1) => {
    setLoading(true);
    try {
      // 获取搜索表单的值
      const filters = searchForm.getFieldsValue();
      // 过滤掉 undefined 或 空字符串
      const validFilters = Object.fromEntries(
        Object.entries(filters).filter(([_, v]) => v != null && v !== '')
      );

      const res = await apiAdminGetJobs(page, pagination.pageSize, validFilters);
      setData(res.data.items); // 根据你的 BaseResponse 结构可能需要调整
      setPagination({ ...pagination, current: page, total: res.data.total });
    } catch (error) {
      console.error(error);
      message.error('获取任务列表失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchJobs(); }, []);

  // --- 事件处理：搜索 ---
  const handleSearch = () => {
    fetchJobs(1); // 搜索时重置到第一页
  };

  const handleReset = () => {
    searchForm.resetFields();
    fetchJobs(1);
  };

  // --- 事件处理：详情 ---
  const showDetail = (record: any) => {
    setCurrentJobDetail(record);
    setDetailOpen(true);
  };

  const handleEdit = (record: any) => {
    setIsEditMode(true);
    modalForm.resetFields();
    // 回填表单
    modalForm.setFieldsValue({
      id: record.id,
      user_id: record.user_id,
      status: record.status,
      // 如果后端返回的是对象，需要 stringify 显示在 TextArea 中供编辑
      request_payload: typeof record.request_payload === 'object' 
        ? JSON.stringify(record.request_payload, null, 2) 
        : record.request_payload,
      error_message: record.error_message
    });
    setModalOpen(true);
  };

  const handleModalOk = async () => {
    try {
      const values = await modalForm.validateFields();
      setModalLoading(true);

      // 处理 JSON 字段 (确保它是合法的 JSON)
      let payloadData = {};
      try {
        if (values.request_payload) {
          payloadData = JSON.parse(values.request_payload);
        }
      } catch (e) {
        message.error('Request Payload 格式不正确，必须是 JSON');
        setModalLoading(false);
        return;
      }

      // 构造提交数据
      const submitData = {
        ...values,
        request_payload: payloadData
      };

      if (isEditMode) {
        // 编辑 (PUT)
        await apiAdminUpdateJob(values.id, submitData);
        message.success('更新成功');
      }

      setModalOpen(false);
      fetchJobs(pagination.current); // 刷新当前页
    } catch (error) {
      console.error(error);
      // message.error 由 axios 拦截器处理或在这里处理
    } finally {
      setModalLoading(false);
    }
  };

  // --- 事件处理：删除 ---
  const handleDelete = async (jobId: string) => {
    try {
      await apiAdminDeleteJob(jobId);
      message.success('删除成功');
      fetchJobs(pagination.current);
    } catch (error) {
      console.error(error);
      message.error('删除失败');
    }
  };

  // --- Columns 定义 ---
  const columns = [
    { title: 'Job ID', dataIndex: 'id', width: 180, ellipsis: true },
    { title: 'User ID', dataIndex: 'user_id', width: 180, ellipsis: true },
    { 
        title: '状态', 
        dataIndex: 'status',
        width: 100,
        render: (status: string) => {
            let color = 'default';
            if (status === 'completed') color = 'green';
            if (status === 'failed') color = 'red';
            if (status === 'running') color = 'blue';
            if (status === 'pending') color = 'orange';
            return <Tag color={color}>{status}</Tag>;
        }
    },
    { title: '创建时间', dataIndex: 'created_at', width: 180, render: (t: string) => formatDate(t, 'YYYY-MM-DD HH:mm:ss') },
    {
        title: '操作',
        width: 200,
        fixed: 'right' as const, // 固定在右侧
        render: (_: any, record: any) => (
            <Space>
                <Button type="link" size="small" onClick={() => showDetail(record)}>详情</Button>
                <Button type="link" size="small" onClick={() => handleEdit(record)}>编辑</Button>
                <Popconfirm 
                  title="确认删除该任务吗?" 
                  onConfirm={() => handleDelete(record.id)}
                  okText="确定"
                  cancelText="取消"
                >
                  <Button type="link" danger size="small">删除</Button>
                </Popconfirm>
            </Space>
        )
    }
  ];

  return (
    <div style={{ padding: 24 }}>
      {/* 1. 搜索与操作栏 */}
      <Card bordered={false} style={{ marginBottom: 16 }}>
        <Form form={searchForm} layout="inline" onFinish={handleSearch}>
          <Form.Item name="job_id" label="Job ID">
            <Input placeholder="输入Job ID" allowClear />
          </Form.Item>
          <Form.Item name="user_id" label="User ID">
            <Input placeholder="输入User ID" allowClear />
          </Form.Item>
          <Form.Item name="status" label="状态">
            <Select placeholder="选择状态" allowClear style={{ width: 120 }}>
              <Option value="pending">Pending</Option>
              <Option value="running">Running</Option>
              <Option value="completed">Completed</Option>
              <Option value="failed">Failed</Option>
            </Select>
          </Form.Item>
          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit" icon={<SearchOutlined />}>搜索</Button>
              <Button onClick={handleReset} icon={<ReloadOutlined />}>重置</Button>
            </Space>
          </Form.Item>
        </Form>
      </Card>

      {/* 2. 表格区域 */}
      <Table 
        columns={columns} 
        dataSource={data} 
        rowKey="id" 
        loading={loading}
        pagination={{
            ...pagination,
            showTotal: (total) => `共 ${total} 条`,
            onChange: (p) => fetchJobs(p)
        }}
        scroll={{ x: 1000 }} // 防止列过多挤压
      />
      
      {/* 3. 详情 Drawer (保持不变) */}
      <Drawer width={600} title="任务详情" open={detailOpen} onClose={() => setDetailOpen(false)}>
        {currentJobDetail && (
            <div>
                <Descriptions column={1} bordered size="small">
                    <Descriptions.Item label="ID">{currentJobDetail.id}</Descriptions.Item>
                    <Descriptions.Item label="User ID">{currentJobDetail.user_id}</Descriptions.Item>
                    <Descriptions.Item label="Status">
                        <Tag>{currentJobDetail.status}</Tag>
                    </Descriptions.Item>
                    <Descriptions.Item label="Created">{formatDate(currentJobDetail.created_at, 'YYYY-MM-DD HH:mm:ss')}</Descriptions.Item>
                    <Descriptions.Item label="Error">{currentJobDetail.error_message || '-'}</Descriptions.Item>
                </Descriptions>
                
                <h4 style={{ marginTop: 20 }}>Request Settings</h4>
                <div style={{ maxHeight: 300, overflow: 'auto', border: '1px solid #f0f0f0', borderRadius: 4 }}>
                    <JsonView src={currentJobDetail.request_payload} collapsed={1} />
                </div>

                <h4 style={{ marginTop: 20 }}>Result Files</h4>
                <div style={{ maxHeight: 300, overflow: 'auto', border: '1px solid #f0f0f0', borderRadius: 4 }}>
                    <JsonView src={currentJobDetail.result_files} collapsed={1} />
                </div>

                <h4 style={{ marginTop: 20 }}>Preview Data</h4>
                <div style={{ maxHeight: 300, overflow: 'auto', border: '1px solid #f0f0f0', borderRadius: 4 }}>
                    <JsonView src={currentJobDetail.preview_data} collapsed={1} />
                </div>
            </div>
        )}
      </Drawer>

      {/* 4. 编辑 Modal */}
      <Modal
        title={isEditMode ? "编辑任务" : "新建任务"}
        open={modalOpen}
        onOk={handleModalOk}
        onCancel={() => setModalOpen(false)}
        confirmLoading={modalLoading}
        width={600}
      >
        <Form form={modalForm} layout="vertical">
          {isEditMode && (
            <Form.Item name="id" label="Job ID">
              <Input disabled />
            </Form.Item>
          )}
          
          <Form.Item 
            name="user_id" 
            label="User ID" 
            rules={[{ required: true, message: '请输入 User ID' }]}
          >
            <Input placeholder="关联的用户ID" />
          </Form.Item>

          <Form.Item 
            name="status" 
            label="状态"
            rules={[{ required: true }]}
          >
             <Select>
                <Option value="awaiting_preview_decision">Awaiting Preview Decision</Option>
                <Option value="awaiting_pagination_review">Awaiting Pagination Review</Option>
                <Option value="completed">Completed</Option>
                <Option value="failed">Failed</Option>
             </Select>
          </Form.Item>

          <Form.Item 
            name="request_payload" 
            label="Request Payload (JSON)"
            rules={[{ required: true, message: '请输入 JSON 配置' }]}
            tooltip="请输入 JSON 格式的字符串"
          >
            <TextArea rows={2} placeholder='{"prompt": "example", "model": "v1"}' />
          </Form.Item>
          
          {isEditMode && (
             <Form.Item name="error_message" label="Error Message">
               <TextArea rows={2} />
             </Form.Item>
          )}
        </Form>
      </Modal>
    </div>
  );
};

export default AdminJobs;
