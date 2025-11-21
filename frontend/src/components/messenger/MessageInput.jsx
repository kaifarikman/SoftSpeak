import { useState, useRef } from 'react';

function MessageInput({
  onSend,
  onSendMedia,
  disabled = false,
  placeholder = "Введите сообщение",
  allowPhotos = false,
  allowVideos = false,
  isMediaUploading = false,
}) {
  const [text, setText] = useState('');
  const photoInputRef = useRef(null);
  const videoInputRef = useRef(null);

  const handleSubmit = (e) => {
    e.preventDefault();
    const trimmed = text.trim();
    if (trimmed && !disabled) {
      onSend(trimmed);
      setText('');
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey && !disabled) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const canSendMedia = Boolean(onSendMedia) && !disabled && !isMediaUploading;

  const triggerMediaSelect = (type) => {
    if (!canSendMedia) return;
    if (type === 'photo') {
      photoInputRef.current?.click();
    } else {
      videoInputRef.current?.click();
    }
  };

  const handleMediaChange = (type, event) => {
    const file = event.target.files?.[0];
    if (file && onSendMedia) {
      onSendMedia(type, file);
    }
    event.target.value = '';
  };

  return (
    <form className="message-input-container" onSubmit={handleSubmit}>
      {(allowPhotos || allowVideos) && (
        <div className="media-buttons">
          {allowPhotos && (
            <button
              type="button"
              className="media-button photo"
              onClick={() => triggerMediaSelect('photo')}
              disabled={!canSendMedia}
              title="Отправить фото"
            >
              📷
            </button>
          )}
          {allowVideos && (
            <button
              type="button"
              className="media-button video"
              onClick={() => triggerMediaSelect('video')}
              disabled={!canSendMedia}
              title="Отправить видео"
            >
              🎬
            </button>
          )}
        </div>
      )}

      <input
        type="text"
        placeholder={disabled ? (placeholder || "Чат недоступен для отправки сообщений") : placeholder}
        className="message-input"
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyPress={handleKeyPress}
        disabled={disabled}
      />
      <button type="submit" className="send-button" disabled={disabled || !text.trim()}>
        <span className="send-button-icon"></span>
      </button>

      <input
        ref={photoInputRef}
        type="file"
        accept="image/*"
        style={{ display: 'none' }}
        onChange={(e) => handleMediaChange('photo', e)}
      />
      <input
        ref={videoInputRef}
        type="file"
        accept="video/*"
        style={{ display: 'none' }}
        onChange={(e) => handleMediaChange('video', e)}
      />
    </form>
  );
}

export default MessageInput;