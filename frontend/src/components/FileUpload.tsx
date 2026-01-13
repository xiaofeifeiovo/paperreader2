/**
 * 文件上传组件
 * ✅ 新增：PDF转换器下拉选择器
 */
import React, { useState, useRef } from 'react';
import { Upload, FileText, X, Info } from 'lucide-react';
import { useDocumentStore } from '../store';
import { useUIStore } from '../store';
import { CONVERTER_OPTIONS, type ConverterType } from '../types/document';

/**
 * 文件上传组件
 */
const FileUpload: React.FC = () => {
  const { uploadDocument, isLoading } = useDocumentStore();
  const { showNotification } = useUIStore();
  const [isDragging, setIsDragging] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [selectedConverter, setSelectedConverter] = useState<ConverterType>('pix2text');  // ✅ 新增状态
  const fileInputRef = useRef<HTMLInputElement>(null);

  // 支持的文件类型
  const ACCEPTED_FILE_TYPES = [
    'application/pdf',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document', // .docx
  ];

  // 最大文件大小 (10MB)
  const MAX_FILE_SIZE = 10 * 1024 * 1024;

  /**
   * 验证文件
   */
  const validateFile = (file: File): boolean => {
    // 检查文件类型
    if (!ACCEPTED_FILE_TYPES.includes(file.type)) {
      showNotification(
        '不支持的文件格式，请上传 PDF 或 DOCX 文件',
        'error'
      );
      return false;
    }

    // 检查文件大小
    if (file.size > MAX_FILE_SIZE) {
      showNotification('文件大小超过 10MB 限制', 'error');
      return false;
    }

    return true;
  };

  /**
   * 处理文件选择
   */
  const handleFileSelect = (file: File) => {
    if (validateFile(file)) {
      setSelectedFile(file);
    }
  };

  /**
   * 处理文件输入变化
   */
  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      handleFileSelect(file);
    }
  };

  /**
   * 处理拖拽事件
   */
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);

    const file = e.dataTransfer.files[0];
    if (file) {
      handleFileSelect(file);
    }
  };

  /**
   * 上传文件
   * ✅ 修改：传递converter参数
   */
  const handleUpload = async () => {
    if (!selectedFile) return;

    // 🔍 调试日志：上传前转换器选择
    console.log('🔍 [FileUpload] ===== 开始上传 =====');
    console.log('🔍 [FileUpload] 上传前转换器选择:', selectedConverter);
    console.log('🔍 [FileUpload] 文件信息:', selectedFile.name, selectedFile.size);

    try {
      await uploadDocument(selectedFile, selectedConverter);  // ✅ 传递选中的转换器

      console.log('✅ [FileUpload] 上传成功');

      const converterLabel = CONVERTER_OPTIONS[selectedConverter].label;
      showNotification(
        `成功上传: ${selectedFile.name} (使用${converterLabel})`,
        'success'
      );

      setSelectedFile(null);
      setSelectedConverter('pix2text');  // ✅ 重置为默认值
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    } catch (error) {
      console.error('❌ [FileUpload] 上传失败:', error);
      showNotification(
        error instanceof Error ? error.message : '上传失败',
        'error'
      );
    }
  };

  /**
   * 取消选择
   * ✅ 修改：重置转换器选择
   */
  const handleCancel = () => {
    setSelectedFile(null);
    setSelectedConverter('pix2text');  // ✅ 重置为默认值
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  return (
    <div className="w-full">
      {/* ✅ 新增：转换器选择下拉菜单 */}
      <div className="mb-4">
        <label
          htmlFor="converter-select"
          className="block text-sm font-medium text-gray-700 mb-2"
        >
          选择PDF转换器
        </label>
        <select
          id="converter-select"
          value={selectedConverter}
          onChange={(e) => setSelectedConverter(e.target.value as ConverterType)}
          disabled={isLoading}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg
                     focus:outline-none focus:ring-2 focus:ring-primary-500
                     disabled:bg-gray-100 disabled:cursor-not-allowed"
        >
          <option value="pix2text">{CONVERTER_OPTIONS.pix2text.label}</option>
          <option value="marker">{CONVERTER_OPTIONS.marker.label}</option>
        </select>

        {/* 转换器说明文字 */}
        <div className="mt-2 flex items-start space-x-2 text-xs text-gray-600">
          <Info className="w-4 h-4 mt-0.5 flex-shrink-0" />
          <p>
            {CONVERTER_OPTIONS[selectedConverter].description}
            {' '}(特性: {CONVERTER_OPTIONS[selectedConverter].features.join('、')})
          </p>
        </div>
      </div>

      {/* 文件上传区域 */}
      <div
        className={`upload-zone ${isDragging ? 'dragging' : ''}`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
          onChange={handleInputChange}
          className="hidden"
          disabled={isLoading}
        />

        {!selectedFile ? (
          <div className="space-y-4">
            <Upload className="w-16 h-16 text-gray-400 mx-auto" />
            <div>
              <p className="text-lg font-medium text-gray-700">
                拖拽文件到此处或点击上传
              </p>
              <p className="text-sm text-gray-500 mt-2">
                支持 PDF 和 DOCX 格式，最大 10MB
              </p>
            </div>
          </div>
        ) : (
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <FileText className="w-12 h-12 text-primary-500" />
              <div className="text-left">
                <p className="font-medium text-gray-800">
                  {selectedFile.name}
                </p>
                <p className="text-sm text-gray-500">
                  {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
                </p>
              </div>
            </div>
            <button
              onClick={(e) => {
                e.stopPropagation();
                handleCancel();
              }}
              className="p-2 hover:bg-gray-200 rounded-full transition-colors duration-200"
            >
              <X className="w-5 h-5 text-gray-500" />
            </button>
          </div>
        )}
      </div>

      {/* 操作按钮 */}
      {selectedFile && (
        <div className="mt-4 flex space-x-3">
          <button
            onClick={handleUpload}
            disabled={isLoading}
            className="btn-primary flex-1"
          >
            {isLoading ? '上传中...' : '开始上传'}
          </button>
          <button
            onClick={handleCancel}
            disabled={isLoading}
            className="btn-secondary flex-1"
          >
            取消
          </button>
        </div>
      )}
    </div>
  );
};

export default FileUpload;
