import { useNavigate } from 'react-router-dom';
import { useState } from 'react';

function FirstStart() {
  const navigate = useNavigate();
  const [nickname, setNickname] = useState('CoolUser123');
  const [age, setAge] = useState('25');
  const [gender, setGender] = useState('М');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (nickname && age) {
      navigate('/success');
    }
  };

  return (
    <div className="container">
      <div className="form-box">
        <h1>Добро пожаловать в SoftSpeak!</h1>
        <p className="subtitle">Перед началом нужно заполнить немного информации</p>
        
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>Никнейм</label>
            <input 
              type="text" 
              placeholder="Никнейм"
              value={nickname}
              onChange={(e) => setNickname(e.target.value)}
              required
            />
          </div>

          <div className="form-group">
            <label>Возраст</label>
            <input 
              type="text" 
              placeholder="Возраст"
              value={age}
              onChange={(e) => setAge(e.target.value)}
              required
            />
          </div>

          <div className="form-group">
            <label>Пол</label>
            <div className="gender-group">
              <div className="radio-group">
                <input 
                  type="radio" 
                  id="male" 
                  name="gender" 
                  value="М"
                  checked={gender === 'М'}
                  onChange={(e) => setGender(e.target.value)}
                />
                <label htmlFor="male" style={{ marginBottom: 0 }}>М</label>
              </div>
              <div className="radio-group">
                <input 
                  type="radio" 
                  id="female" 
                  name="gender" 
                  value="Ж"
                  checked={gender === 'Ж'}
                  onChange={(e) => setGender(e.target.value)}
                />
                <label htmlFor="female" style={{ marginBottom: 0 }}>Ж</label>
              </div>
            </div>
          </div>

          <button type="submit" className="btn">Начать</button>
        </form>
      </div>
    </div>
  );
}

export default FirstStart;
