import { useEffect, useState } from 'react';
import '../../css/components/OnboardingOverlay.css';

const STEPS = [
  {
    title: 'Анкета',
    text: 'Сначала заполни психологический опрос. Он нужен, чтобы система понимала, с кем тебе будет проще говорить.',
  },
  {
    title: 'Матчинг',
    text: 'Потом включается поиск собеседника. Совпадения строятся по ответам и дополнительным настройкам.',
  },
  {
    title: 'Анонимность',
    text: 'До взаимного раскрытия имя скрыто. Личность и профиль открываются только когда оба этого хотят.',
  },
];

function OnboardingOverlay({ onFinish }) {
  const [step, setStep] = useState(0);

  useEffect(() => {
    const savedStep = Number(localStorage.getItem('onboarding_step') || 0);
    if (savedStep >= 0 && savedStep < STEPS.length) {
      setStep(savedStep);
    }
  }, []);

  const persistStep = (nextStep) => {
    localStorage.setItem('onboarding_step', String(nextStep));
    setStep(nextStep);
  };

  const handleNext = () => {
    if (step >= STEPS.length - 1) {
      localStorage.setItem('onboarding_done', 'true');
      localStorage.removeItem('onboarding_step');
      if (typeof onFinish === 'function') {
        onFinish();
      }
      return;
    }
    persistStep(step + 1);
  };

  const handleBack = () => {
    persistStep(Math.max(0, step - 1));
  };

  const current = STEPS[step];

  return (
    <div className="onboarding-overlay" role="dialog" aria-modal="true" aria-label="Тур по приложению">
      <div className="onboarding-panel">
        <div className="onboarding-progress">
          {STEPS.map((item, index) => (
            <span key={item.title} className={index <= step ? 'active' : ''} />
          ))}
        </div>
        <div className="onboarding-step">
          <p className="onboarding-step-index">Шаг {step + 1} из {STEPS.length}</p>
          <h2>{current.title}</h2>
          <p>{current.text}</p>
        </div>
        <div className="onboarding-actions">
          <button type="button" className="onboarding-button secondary" onClick={handleBack} disabled={step === 0}>
            Назад
          </button>
          <button type="button" className="onboarding-button primary" onClick={handleNext}>
            {step === STEPS.length - 1 ? 'Начать' : 'Дальше'}
          </button>
        </div>
      </div>
    </div>
  );
}

export default OnboardingOverlay;
