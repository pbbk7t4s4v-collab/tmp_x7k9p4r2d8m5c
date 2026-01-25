import React, { useState, useEffect } from 'react';
import { Table, Button, Tag, Space, Modal, Form, Switch, message, Input } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { getAdminUsersApi, updateAdminUserApi, deleteAdminUserApi } from '@/api/admin';
import { formatDate } from '@/utils/time';

interface User {
  id: string;
  email: string;
  username: string;
  full_name: string;
  is_active: boolean;
  is_superuser: boolean;
  created_at: string;
}

const AdminUsers: React.FC = () => {
  const [data, setData] = useState<User[]>([]);
  const [loading, setLoading] = useState(false);
  const [pagination, setPagination] = useState({ current: 1, pageSize: 10, total: 0 });
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [form] = Form.useForm();

  const fetchUsers = async (page = 1, size = 10, email = '') => {
    setLoading(true);
    try {
      const res = await getAdminUsersApi(page, size, email);
      setData(res.data.items);
      setPagination({ ...pagination, current: page, total: res.data.total });
    } catch (error) {
      message.error('加载用户失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, []);

  const handleEdit = (user: User) => {
    setEditingUser(user);
    form.setFieldsValue(user);
  };

  const handleSave = async () => {
    if (!editingUser) {
        message.error('请先选择用户');
        return;
    }
    try {
      const values = await form.validateFields();
      await updateAdminUserApi(editingUser?.id, values);
      message.success('更新成功');
      setEditingUser(null);
      fetchUsers(pagination.current);
    } catch (error) {
      message.error('更新失败');
    }
  };

  const handleDelete = (id: string) => {
    Modal.confirm({
      title: '确认删除?',
      content: '删除操作不可恢复',
      onOk: async () => {
        await deleteAdminUserApi(id);
        message.success('删除成功');
        fetchUsers(pagination.current);
      },
    });
  };

  const columns: ColumnsType<User> = [
    { title: 'ID', dataIndex: 'id', ellipsis: true },
    { title: '用户名', dataIndex: 'username' },
    { title: '全名', dataIndex: 'full_name' },
    { title: '邮箱', dataIndex: 'email' },
    { 
      title: '状态', 
      dataIndex: 'is_active',
      width: 80,
      render: (active) => active ? <Tag color="green">正常</Tag> : <Tag color="red">禁用</Tag>
    },
    { 
      title: '角色', 
      dataIndex: 'is_superuser',
      width: 80,
      render: (isSuper) => isSuper ? <Tag color="gold">管理员</Tag> : <Tag color="blue">用户</Tag>
    },
    { 
        title: '注册时间', 
        dataIndex: 'created_at', 
        width: 250,
        render: (val) => formatDate(val, 'YYYY年MM月DD日 HH:mm:ss') },
    {
      title: '操作',
      key: 'action',
      width: 180,
      render: (_, record) => (
        <Space size="middle">
          <Button type="link" onClick={() => handleEdit(record)}>编辑</Button>
          <Button type="link" danger onClick={() => handleDelete(record.id)}>删除</Button>
        </Space>
      ),
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      <div style={{ marginBottom: 16 }}>
        <Input.Search 
          placeholder="搜索邮箱" 
          onSearch={(val) => fetchUsers(1, 10, val)} 
          style={{ width: 200 }} 
        />
      </div>
      <Table 
        columns={columns} 
        dataSource={data} 
        rowKey="id"
        loading={loading}
        pagination={{
          ...pagination,
          onChange: (page, size) => fetchUsers(page, size),
        }}
      />

      <Modal
        title="编辑用户"
        open={!!editingUser}
        onOk={handleSave}
        onCancel={() => setEditingUser(null)}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="full_name" label="全名">
            <Input />
          </Form.Item>
          <Form.Item name="is_active" label="账号状态" valuePropName="checked">
            <Switch checkedChildren="激活" unCheckedChildren="禁用" />
          </Form.Item>
          <Form.Item name="is_superuser" label="管理员权限" valuePropName="checked">
            <Switch checkedChildren="是" unCheckedChildren="否" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default AdminUsers;