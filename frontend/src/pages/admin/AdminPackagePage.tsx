// src/pages/AdminPackagePage.tsx
import React, { useState, useEffect } from 'react';
import {
    Table, Button, Space, message, Modal, Form, Input,
    InputNumber, Switch, Tag, Popconfirm, Card, Typography, Select, Row,Col
} from 'antd';
import {
    PlusOutlined, EditOutlined, DeleteOutlined, CoffeeOutlined,
    GiftOutlined, TrophyOutlined, EyeOutlined, EyeInvisibleOutlined
} from '@ant-design/icons';
import type { TableProps } from 'antd';
import {
    apiAdminGetPackages,
    apiAdminCreatePackage,
    apiAdminUpdatePackage,
    apiAdminDeletePackage
} from '@/api/admin';
import type { RechargePackage, RechargePackageCreate, RechargePackageUpdate } from '@/types/tcoin';

const { Title } = Typography;
const { Option } = Select;

// 图标 key 映射，用于 Select 和 Table
const ICON_MAP: Record<string, { label: string; icon: React.ReactNode }> = {
    'coffee': { label: '咖啡', icon: <CoffeeOutlined /> },
    'gift': { label: '礼物', icon: <GiftOutlined /> },
    'trophy': { label: '奖杯', icon: <TrophyOutlined /> },
};

// 价格格式化
const formatCents = (cents: number): string => `￥${(cents / 100).toFixed(2)}`;

const AdminPackagePage: React.FC = () => {
    const [packages, setPackages] = useState<RechargePackage[]>([]);
    const [loading, setLoading] = useState(true);
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [editingPackage, setEditingPackage] = useState<RechargePackage | null>(null);
    const [form] = Form.useForm<RechargePackageCreate>();

    // --- 数据获取 ---
    const fetchPackages = async () => {
        setLoading(true);
        try {
            const response = await apiAdminGetPackages();
            // 按 display_order 排序
            const sortedData = response.data.sort((a, b) => a.display_order - b.display_order);
            setPackages(sortedData);
        } catch (error) {
            message.error('获取套餐列表失败');
            console.error(error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchPackages();
    }, []);

    // --- Modal 和 表单逻辑 ---
    const showCreateModal = () => {
        setEditingPackage(null);
        form.resetFields();
        form.setFieldsValue({ // 设置默认值
            is_active: true,
            best_value: false,
            display_order: 0,
        });
        setIsModalOpen(true);
    };

    const showEditModal = (record: RechargePackage) => {
        setEditingPackage(record);
        form.setFieldsValue(record); // 填充表单
        setIsModalOpen(true);
    };

    const handleModalCancel = () => {
        setIsModalOpen(false);
        setEditingPackage(null);
    };

    const handleModalOk = async () => {
        try {
            const values = await form.validateFields();
            
            if (editingPackage) {
                // --- 更新逻辑 ---
                const updateData: RechargePackageUpdate = { ...values };
                await apiAdminUpdatePackage(editingPackage.id, updateData);
                message.success('套餐更新成功');
            } else {
                // --- 创建逻辑 ---
                const createData: RechargePackageCreate = { ...values };
                await apiAdminCreatePackage(createData);
                message.success('套餐创建成功');
            }
            setIsModalOpen(false);
            setEditingPackage(null);
            fetchPackages(); // 重新加载数据
        } catch (errorInfo) {
            console.error('表单验证失败:', errorInfo);
            message.error('操作失败，请检查表单');
        }
    };

    // --- 删除逻辑 ---
    const handleDelete = async (packageId: string) => {
        try {
            await apiAdminDeletePackage(packageId);
            message.success('套餐删除成功');
            fetchPackages(); // 重新加载数据
        } catch (error) {
            message.error('删除失败');
            console.error(error);
        }
    };

    // --- 表格列定义 ---
    const columns: TableProps<RechargePackage>['columns'] = [
        {
            title: '排序',
            dataIndex: 'display_order',
            key: 'display_order',
            width: 80,
            sorter: (a, b) => a.display_order - b.display_order,
        },
        {
            title: '套餐名称',
            dataIndex: 'name',
            key: 'name',
            width: 150,
        },
        {
            title: '套餐 ID',
            dataIndex: 'id',
            key: 'id',
            width: 150,
            render: (id: string) => <Tag>{id}</Tag>,
        },
        {
            title: 'T币',
            dataIndex: 'tcoins',
            key: 'tcoins',
            width: 100,
            render: (tcoins: number) => `${tcoins.toLocaleString()} 币`,
        },
        {
            title: '价格',
            dataIndex: 'amount_cents',
            key: 'amount_cents',
            width: 120,
            render: (cents: number) => <Tag color="blue">{formatCents(cents)}</Tag>,
        },
        {
            title: '状态',
            dataIndex: 'is_active',
            key: 'is_active',
            width: 100,
            render: (isActive: boolean) => (
                <Tag color={isActive ? 'success' : 'default'} icon={isActive ? <EyeOutlined /> : <EyeInvisibleOutlined />}>
                    {isActive ? '可用' : '禁用'}
                </Tag>
            ),
        },
        {
            title: '推荐',
            dataIndex: 'best_value',
            key: 'best_value',
            width: 100,
            render: (isBest: boolean, record) => (
                isBest ? <Tag color="gold">{record.ribbon_text || '推荐'}</Tag> : <Tag>否</Tag>
            ),
        },
        {
            title: '图标',
            dataIndex: 'icon_key',
            key: 'icon_key',
            width: 80,
            render: (iconKey: string) => ICON_MAP[iconKey] ? ICON_MAP[iconKey].icon : null,
        },
        {
            title: '操作',
            key: 'action',
            fixed: 'right',
            width: 150,
            render: (_, record) => (
                <Space size="middle">
                    <Button type="link" icon={<EditOutlined />} onClick={() => showEditModal(record)}>
                        编辑
                    </Button>
                    <Popconfirm
                        title={`确定删除 "${record.name}" 吗？`}
                        onConfirm={() => handleDelete(record.id)}
                        okText="删除"
                        okType="danger"
                        cancelText="取消"
                    >
                        <Button type="link" danger icon={<DeleteOutlined />}>
                            删除
                        </Button>
                    </Popconfirm>
                </Space>
            ),
        },
    ];

    return (
        <div style={{ padding: '24px' }}>
            <Card bordered={false}>
                <Title level={3} style={{ marginTop: 0, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    套餐管理
                    <Button
                        type="primary"
                        icon={<PlusOutlined />}
                        onClick={showCreateModal}
                    >
                        新建套餐
                    </Button>
                </Title>

                <Table
                    columns={columns}
                    dataSource={packages}
                    rowKey="id"
                    loading={loading}
                    scroll={{ x: 'max-content' }}
                    pagination={{ pageSize: 10 }}
                />
            </Card>

            <Modal
                title={editingPackage ? `编辑套餐 - ${editingPackage.name}` : '新建套餐'}
                open={isModalOpen}
                onOk={handleModalOk}
                onCancel={handleModalCancel}
                destroyOnClose
            >
                <Form
                    form={form}
                    layout="vertical"
                    name="packageForm"
                    initialValues={{ is_active: true, best_value: false, display_order: 0 }}
                >
                    <Form.Item
                        name="id"
                        label="套餐 ID (e.g., 'pkg_100')"
                        rules={[{ required: true, message: '必须填写唯一ID' }]}
                    >
                        <Input disabled={!!editingPackage} placeholder="创建后不可修改" />
                    </Form.Item>
                    
                    <Form.Item
                        name="name"
                        label="套餐名称"
                        rules={[{ required: true, message: '必须填写名称' }]}
                    >
                        <Input placeholder="例如：超值包" />
                    </Form.Item>

                    <Row gutter={16}>
                        <Col span={12}>
                            <Form.Item
                                name="tcoins"
                                label="T币数量"
                                rules={[{ required: true, message: '必须填写T币数' }]}
                            >
                                <InputNumber style={{ width: '100%' }} min={1} />
                            </Form.Item>
                        </Col>
                        <Col span={12}>
                            <Form.Item
                                name="amount_cents"
                                label="价格 (单位：分)"
                                rules={[{ required: true, message: '必须填写价格' }]}
                            >
                                <InputNumber style={{ width: '100%' }} min={1} placeholder="例如: 4500 (即 ￥45.00)" />
                            </Form.Item>
                        </Col>
                    </Row>
                    
                    <Form.Item
                        name="icon_key"
                        label="前端显示图标"
                    >
                        <Select placeholder="选择一个图标" allowClear>
                            {Object.keys(ICON_MAP).map(key => (
                                <Option key={key} value={key}>
                                    <Space>
                                        {ICON_MAP[key].icon}
                                        {ICON_MAP[key].label}
                                    </Space>
                                </Option>
                            ))}
                        </Select>
                    </Form.Item>

                    <Form.Item
                        name="ribbon_text"
                        label="徽标文字"
                    >
                        <Input placeholder="例如：9折优惠 (留空则不显示)" />
                    </Form.Item>

                    <Form.Item
                        name="display_order"
                        label="显示排序 (数字越小越靠前)"
                        rules={[{ required: true, message: '必须填写排序' }]}
                    >
                        <InputNumber style={{ width: '100%' }} />
                    </Form.Item>

                    <Space>
                        <Form.Item name="is_active" label="是否可用" valuePropName="checked">
                            <Switch checkedChildren="可用" unCheckedChildren="禁用" />
                        </Form.Item>
                        <Form.Item name="best_value" label="是否推荐" valuePropName="checked">
                            <Switch checkedChildren="推荐" unCheckedChildren="普通" />
                        </Form.Item>
                    </Space>
                </Form>
            </Modal>
        </div>
    );
};

export default AdminPackagePage;