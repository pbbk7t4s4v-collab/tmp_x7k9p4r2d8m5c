// src/pages/admin/AdminRedeemCodePage.tsx
import React, { useState, useEffect } from 'react';
import {
    Table, Button, Space, message, Modal, Form, Input,
    InputNumber, Tag, Popconfirm, Card, Typography, DatePicker
} from 'antd';
import {
    PlusOutlined, DeleteOutlined, GiftOutlined, CheckCircleOutlined, CloseCircleOutlined, RobotOutlined
} from '@ant-design/icons';
import type { TableProps } from 'antd';
import {
    apiAdminCreateRedeemCode,
    apiAdminGetRedeemCodes,
    apiAdminDeleteRedeemCode,
    apiAdminEncryptRedeemCode
} from '@/api/admin';
import type { RedeemCode, RedeemCodeCreate } from '@/types/tcoin';
import { formatDate } from '@/utils/time';
import dayjs from 'dayjs';

const { Title } = Typography;

const AdminRedeemCodePage: React.FC = () => {
    const [codes, setCodes] = useState<RedeemCode[]>([]);
    const [loading, setLoading] = useState(true);
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [form] = Form.useForm<RedeemCodeCreate>();
    const [pagination, setPagination] = useState({ current: 1, pageSize: 10, total: 0 });
    const [filters, setFilters] = useState<{ code?: string; is_used?: boolean }>({});
    const [generatingCode, setGeneratingCode] = useState(false);

    // --- 数据获取 ---
    const fetchCodes = async (page = 1, pageSize = 10) => {
        setLoading(true);
        try {
            const response = await apiAdminGetRedeemCodes(page, pageSize, filters);
            setCodes(response.data.items);
            setPagination({
                current: response.data.page,
                pageSize: response.data.size,
                total: response.data.total
            });
        } catch (error) {
            message.error('获取兑换码列表失败');
            console.error(error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchCodes(pagination.current, pagination.pageSize);
    }, [filters]);

    // --- Modal 和 表单逻辑 ---
    const showCreateModal = () => {
        form.resetFields();
        setIsModalOpen(true);
    };

    const handleModalCancel = () => {
        setIsModalOpen(false);
    };
    // 生成加密兑换码
    const handleGenerateCode = async () => {
        try {
            // 先验证T币数量（必填项）
            const tcoins = form.getFieldValue('tcoins');
            if (!tcoins || tcoins < 1) {
                message.warning('请先填写T币数量');
                return;
            }

            setGeneratingCode(true);
            const values = form.getFieldsValue();
            
            const encryptData = {
                tcoins: values.tcoins,
                valid_from: values.valid_from ? dayjs(values.valid_from).toISOString() : null,
                valid_until: values.valid_until ? dayjs(values.valid_until).toISOString() : null,
                notes: values.notes || null,
            };
            
            const response = await apiAdminEncryptRedeemCode(encryptData);
            form.setFieldsValue({ code: response.data.code });
            message.success('兑换码生成成功');
        } catch (error: any) {
            const errorMessage = error.response?.data?.detail || '生成兑换码失败';
            message.error(errorMessage);
            console.error(error);
        } finally {
            setGeneratingCode(false);
        }
    };


    const handleModalOk = async () => {
        try {
            const values = await form.validateFields();
            
            const createData: RedeemCodeCreate = {
                ...values,
                valid_from: values.valid_from ? dayjs(values.valid_from).toISOString() : null,
                valid_until: values.valid_until ? dayjs(values.valid_until).toISOString() : null,
            };
            
            await apiAdminCreateRedeemCode(createData);
            message.success('兑换码创建成功');
            setIsModalOpen(false);
            fetchCodes(pagination.current, pagination.pageSize);
        } catch (errorInfo: any) {
            console.error('表单验证失败:', errorInfo);
            if (errorInfo.errorFields) {
                message.error('请检查表单输入');
            } else {
                message.error('创建失败');
            }
        }
    };

    // --- 删除逻辑 ---
    const handleDelete = async (codeId: string) => {
        try {
            await apiAdminDeleteRedeemCode(codeId);
            message.success('兑换码删除成功');
            fetchCodes(pagination.current, pagination.pageSize);
        } catch (error: any) {
            const errorMessage = error.response?.data?.detail || '删除失败';
            message.error(errorMessage);
            console.error(error);
        }
    };

    // --- 表格列定义 ---
    const columns: TableProps<RedeemCode>['columns'] = [
        {
            title: '兑换码',
            dataIndex: 'code',
            key: 'code',
            width: 200,
            render: (code: string) => <Tag color="blue" style={{ fontSize: '14px' }}>{code}</Tag>,
        },
        {
            title: 'T币数量',
            dataIndex: 'tcoins',
            key: 'tcoins',
            width: 120,
            render: (tcoins: number) => <Tag color="green">{tcoins.toLocaleString()} 币</Tag>,
        },
        {
            title: '状态',
            dataIndex: 'is_used',
            key: 'is_used',
            width: 100,
            render: (isUsed: boolean) => (
                <Tag 
                    color={isUsed ? 'default' : 'success'} 
                    icon={isUsed ? <CloseCircleOutlined /> : <CheckCircleOutlined />}
                >
                    {isUsed ? '已使用' : '未使用'}
                </Tag>
            ),
            filters: [
                { text: '未使用', value: false },
                { text: '已使用', value: true },
            ],
            onFilter: (value, record) => record.is_used === value,
        },
        {
            title: '使用时间',
            dataIndex: 'used_at',
            key: 'used_at',
            width: 180,
            render: (usedAt: string | null) => usedAt ? formatDate(usedAt, 'YYYY-MM-DD HH:mm:ss') : '-',
        },
        {
            title: '使用用户',
            dataIndex: 'used_by_user_id',
            key: 'used_by_user_id',
            width: 150,
            render: (userId: string | null) => userId ? <Tag>{userId.substring(0, 8)}...</Tag> : '-',
        },
        {
            title: '有效期开始',
            dataIndex: 'valid_from',
            key: 'valid_from',
            width: 180,
            render: (validFrom: string | null) => validFrom ? formatDate(validFrom, 'YYYY-MM-DD HH:mm:ss') : '-',
        },
        {
            title: '有效期结束',
            dataIndex: 'valid_until',
            key: 'valid_until',
            width: 180,
            render: (validUntil: string | null) => validUntil ? formatDate(validUntil, 'YYYY-MM-DD HH:mm:ss') : '-',
        },
        {
            title: '备注',
            dataIndex: 'notes',
            key: 'notes',
            ellipsis: true,
        },
        {
            title: '创建时间',
            dataIndex: 'created_at',
            key: 'created_at',
            width: 180,
            render: (createdAt: string) => formatDate(createdAt, 'YYYY-MM-DD HH:mm:ss'),
            sorter: (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime(),
        },
        {
            title: '操作',
            key: 'action',
            fixed: 'right',
            width: 100,
            render: (_, record) => (
                <Popconfirm
                    title={`确定删除兑换码 "${record.code}" 吗？`}
                    description={record.is_used ? '此兑换码已被使用，删除后无法恢复记录' : '删除后无法恢复'}
                    onConfirm={() => handleDelete(record.id)}
                    okText="删除"
                    okType="danger"
                    cancelText="取消"
                >
                    <Button type="link" danger icon={<DeleteOutlined />} disabled={record.is_used}>
                        删除
                    </Button>
                </Popconfirm>
            ),
        },
    ];

    const handleTableChange = (newPagination: any) => {
        setPagination({
            ...pagination,
            current: newPagination.current,
            pageSize: newPagination.pageSize,
        });
        fetchCodes(newPagination.current, newPagination.pageSize);
    };

    return (
        <div style={{ padding: '24px' }}>
            <Card bordered={false}>
                <Title level={3} style={{ marginTop: 0, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    兑换码管理
                    <Button
                        type="primary"
                        icon={<PlusOutlined />}
                        onClick={showCreateModal}
                    >
                        新建兑换码
                    </Button>
                </Title>

                <Table
                    columns={columns}
                    dataSource={codes}
                    rowKey="id"
                    loading={loading}
                    scroll={{ x: 'max-content' }}
                    pagination={{
                        current: pagination.current,
                        pageSize: pagination.pageSize,
                        total: pagination.total,
                        showSizeChanger: true,
                        showTotal: (total) => `共 ${total} 条`,
                    }}
                    onChange={handleTableChange}
                />
            </Card>

            <Modal
                title="新建兑换码"
                open={isModalOpen}
                onOk={handleModalOk}
                onCancel={handleModalCancel}
                destroyOnClose
                width={600}
            >
                <Form
                    form={form}
                    layout="vertical"
                    name="redeemCodeForm"
                >
                    
                    <Form.Item
                        name="tcoins"
                        label="T币数量"
                        rules={[
                            { required: true, message: '必须填写T币数量' },
                            { type: 'number', min: 1, message: 'T币数量必须大于0' },
                        ]}
                    >
                        <InputNumber style={{ width: '100%' }} min={1} placeholder="例如：100" />
                    </Form.Item>

                    <Form.Item
                        name="valid_from"
                        label="有效期开始时间（可选）"
                    >
                        <DatePicker 
                            showTime 
                            style={{ width: '100%' }} 
                            format="YYYY-MM-DD HH:mm:ss"
                        />
                    </Form.Item>

                    <Form.Item
                        name="valid_until"
                        label="有效期结束时间（可选）"
                    >
                        <DatePicker 
                            showTime 
                            style={{ width: '100%' }} 
                            format="YYYY-MM-DD HH:mm:ss"
                        />
                    </Form.Item>

                    <Form.Item
                        name="notes"
                        label="备注（可选）"
                    >
                        <Input.TextArea 
                            rows={3} 
                            placeholder="例如：活动赠送、用户补偿等"
                            maxLength={500}
                            showCount
                        />
                    </Form.Item>

                    
                    <Form.Item
                        name="code"
                        label="兑换码"
                        rules={[
                            { required: true, message: '必须填写兑换码' },
                            { min: 6, message: '兑换码必须至少6个字符' },
                            { max: 20, message: '兑换码必须不超过20个字符（Timo + 16个字符）' },
                            { pattern: /^Timo[A-Z2-9]{6,16}$/, message: '兑换码格式不正确，应为Timo开头后跟6-16位大写字母或数字' },
                        ]}
                    >
                        <Input 
                            placeholder="手动输入或点击右侧图标自动生成（以Timo开头）" 
                            suffix={
                                <RobotOutlined 
                                    onClick={handleGenerateCode}
                                    style={{ 
                                        cursor: 'pointer', 
                                        color: generatingCode ? '#1890ff' : '#999',
                                        fontSize: '16px'
                                    }}
                                    spin={generatingCode}
                                    title="根据配置生成兑换码"
                                />
                            }
                        />
                    </Form.Item>
                </Form>
            </Modal>
        </div>
    );
};

export default AdminRedeemCodePage;

