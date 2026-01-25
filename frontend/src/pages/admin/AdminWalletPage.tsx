import React, { useState, useEffect } from 'react';
import { 
  Table, Tag, Button, Modal, Drawer, Descriptions, 
  Form, Input, InputNumber, Space, Card, message, Statistic, Divider 
} from 'antd';
import { SearchOutlined, ReloadOutlined, HistoryOutlined, PayCircleOutlined } from '@ant-design/icons';
import { apiAdminGetWallets, apiAdminAdjustBalance, apiAdminGetTransactions } from '@/api/admin';
import { formatDate } from '@/utils/time';

const AdminWallets: React.FC = () => {
  // --- Wallets State ---
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [pagination, setPagination] = useState({ current: 1, pageSize: 10, total: 0 });
  const [searchForm] = Form.useForm();

  // --- Adjust Balance Modal State ---
  const [adjustOpen, setAdjustOpen] = useState(false);
  const [adjustLoading, setAdjustLoading] = useState(false);
  const [currentWallet, setCurrentWallet] = useState<any>(null);
  const [adjustForm] = Form.useForm();

  // --- Transaction Logs Drawer State ---
  const [logOpen, setLogOpen] = useState(false);
  const [logData, setLogData] = useState([]);
  const [logLoading, setLogLoading] = useState(false);
  const [logPagination, setLogPagination] = useState({ current: 1, pageSize: 10, total: 0 });
  const [currentUserIdForLog, setCurrentUserIdForLog] = useState<string | null>(null);

  // ================= 1. Wallet Logic =================
  const fetchWallets = async (page = 1) => {
    setLoading(true);
    try {
      const filters = searchForm.getFieldsValue();
      const res = await apiAdminGetWallets(page, pagination.pageSize, filters);
      setData(res.data.items);
      setPagination({ ...pagination, current: page, total: res.data.total });
    } catch (error) {
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchWallets(); }, []);

  const handleSearch = () => fetchWallets(1);
  const handleReset = () => {
    searchForm.resetFields();
    fetchWallets(1);
  };

  // ================= 2. Adjust Balance Logic =================
  const showAdjustModal = (record: any) => {
    setCurrentWallet(record);
    adjustForm.resetFields();
    // 默认填入 user_id，不可修改
    adjustForm.setFieldsValue({ user_id: record.user_id, amount: 0 });
    setAdjustOpen(true);
  };

  const handleAdjustSubmit = async () => {
    try {
      const values = await adjustForm.validateFields();
      if (values.amount === 0) {
        message.warning('变动金额不能为 0');
        return;
      }
      setAdjustLoading(true);
      await apiAdminAdjustBalance(values);
      message.success('余额调整成功');
      setAdjustOpen(false);
      fetchWallets(pagination.current); // 刷新列表
    } catch (error) {
      console.error(error);
    } finally {
      setAdjustLoading(false);
    }
  };

  // ================= 3. Transaction Log Logic =================
  const showLogDrawer = (userId: string) => {
    setCurrentUserIdForLog(userId);
    setLogOpen(true);
    fetchLogs(userId, 1);
  };

  const fetchLogs = async (userId: string, page = 1) => {
    setLogLoading(true);
    try {
      const res = await apiAdminGetTransactions(page, logPagination.pageSize, { user_id: userId });
      setLogData(res.data.items);
      setLogPagination({ ...logPagination, current: page, total: res.data.total });
    } catch (error) {
      console.error(error);
    } finally {
      setLogLoading(false);
    }
  };

  // ================= UI Render =================

  const walletColumns = [
    { title: 'User ID', dataIndex: 'user_id', ellipsis: true },
    { 
      title: '当前余额 (T币)', 
      dataIndex: 'balance', 
      render: (val: number) => <Statistic value={val} valueStyle={{ fontSize: 16, fontWeight: 'bold', color: val < 0 ? 'red' : '#3f8600' }} /> 
    },
    { title: '更新时间', width: 200, dataIndex: 'updated_at', render: (t: string) => formatDate(t, 'YYYY年MM月DD日 HH:mm:ss') },
    {
      title: '操作',
      width: 300,
      render: (_: any, record: any) => (
        <Space>
          <Button type="primary" size="small" icon={<PayCircleOutlined />} onClick={() => showAdjustModal(record)}>
            调整余额
          </Button>
          <Button size="small" icon={<HistoryOutlined />} onClick={() => showLogDrawer(record.user_id)}>
            流水记录
          </Button>
        </Space>
      )
    }
  ];

  const logColumns = [
    { 
        title: '类型', 
        dataIndex: 'transaction_type',
        width: 120,
        render: (type: string) => {
            const colors: any = { 
                RECHARGE: 'green', CONSUMPTION: 'blue', REFUND: 'orange', 
                REWARD: 'gold', ADMIN_ADJUST: 'purple' 
            };
            return <Tag color={colors[type] || 'default'}>{type}</Tag>;
        }
    },
    { 
        title: '变动金额', 
        dataIndex: 'amount',
        render: (val: number) => (
            <span style={{ color: val > 0 ? 'green' : 'red', fontWeight: 'bold' }}>
                {val > 0 ? `+${val}` : val}
            </span>
        )
    },
    { title: '变动后余额', dataIndex: 'balance_after' },
    { title: '备注', width: 200, dataIndex: 'notes', ellipsis: true },
    { title: '时间', dataIndex: 'created_at', width: 200, render: (t: string) => formatDate(t,'YYYY年MM月DD日 HH:mm:ss' ) },
  ];

  return (
    <div style={{ padding: 24 }}>
      {/* 搜索栏 */}
      <Card bordered={false} style={{ marginBottom: 16 }}>
        <Form form={searchForm} layout="inline" onFinish={handleSearch}>
          <Form.Item name="user_id" label="User ID">
            <Input placeholder="输入 User ID" allowClear />
          </Form.Item>
          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit" icon={<SearchOutlined />}>搜索</Button>
              <Button onClick={handleReset} icon={<ReloadOutlined />}>重置</Button>
            </Space>
          </Form.Item>
        </Form>
      </Card>

      {/* 钱包列表 */}
      <Table 
        columns={walletColumns} 
        dataSource={data} 
        rowKey="user_id" // 注意这里用 user_id 作为 key
        loading={loading}
        pagination={{
            ...pagination,
            onChange: (p) => fetchWallets(p)
        }}
      />

      {/* 余额调整弹窗 */}
      <Modal
        title="人工调整余额"
        open={adjustOpen}
        onOk={handleAdjustSubmit}
        onCancel={() => setAdjustOpen(false)}
        confirmLoading={adjustLoading}
      >
        <Form form={adjustForm} layout="vertical">
            <Form.Item name="user_id" label="当前操作用户">
                <Input value={currentWallet?.user_id} disabled />
            </Form.Item>
            <Form.Item label="当前余额">
                 <span style={{ fontSize: 18, fontWeight: 'bold' }}>{currentWallet?.balance}</span>
            </Form.Item>
            <Form.Item 
                name="amount" 
                label="变动金额 (正数为增加，负数为扣除)" 
                rules={[{ required: true, message: '请输入变动金额' }]}
            >
                <InputNumber style={{ width: '100%' }} placeholder="例如: 100 或 -50" />
            </Form.Item>
            <Form.Item name="notes" label="调整备注" rules={[{ required: true }]}>
                <Input.TextArea rows={3} placeholder="请填写调整原因，例如：系统补偿、退款等" />
            </Form.Item>
        </Form>
      </Modal>

      {/* 流水记录抽屉 */}
      <Drawer 
        title="交易流水记录" 
        width={700} 
        open={logOpen} 
        onClose={() => setLogOpen(false)}
      >
        <Descriptions column={1} size="small" style={{ marginBottom: 20 }}>
             <Descriptions.Item label="User ID">{currentUserIdForLog}</Descriptions.Item>
        </Descriptions>
        <Table
            columns={logColumns}
            dataSource={logData}
            rowKey="id"
            loading={logLoading}
            size="small"
            pagination={{
                ...logPagination,
                size: "small",
                onChange: (p) => currentUserIdForLog && fetchLogs(currentUserIdForLog, p)
            }}
        />
      </Drawer>
    </div>
  );
};

export default AdminWallets;