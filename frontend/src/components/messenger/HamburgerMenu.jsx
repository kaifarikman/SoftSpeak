import { useEffect, useMemo, useRef, useState } from 'react';
import '../../css/components/HamburgerMenu.css';

function HamburgerMenu({ sections, activeSection, onSelectSection }) {
  const [isOpen, setIsOpen] = useState(false);
  const menuRef = useRef(null);

  const mobileSections = useMemo(() => sections || [], [sections]);

  useEffect(() => {
    setIsOpen(false);
  }, [activeSection]);

  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth > 768) {
        setIsOpen(false);
      }
    };
    const handleKeyDown = (event) => {
      if (event.key === 'Escape') {
        setIsOpen(false);
      }
    };
    const handleClickOutside = (event) => {
      if (menuRef.current && !menuRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };

    window.addEventListener('resize', handleResize);
    window.addEventListener('keydown', handleKeyDown);
    document.addEventListener('mousedown', handleClickOutside);

    return () => {
      window.removeEventListener('resize', handleResize);
      window.removeEventListener('keydown', handleKeyDown);
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  const handleSelect = (sectionId) => {
    if (typeof onSelectSection === 'function') {
      onSelectSection(sectionId);
    }
    setIsOpen(false);
  };

  return (
    <div className="hamburger-menu" ref={menuRef}>
      <button
        type="button"
        className={`hamburger-trigger ${isOpen ? 'open' : ''}`}
        aria-label={isOpen ? 'Закрыть меню' : 'Открыть меню'}
        aria-expanded={isOpen}
        aria-controls="mobile-navigation"
        onClick={() => setIsOpen((current) => !current)}
      >
        <span />
        <span />
        <span />
      </button>
      <div
        id="mobile-navigation"
        className={`hamburger-panel ${isOpen ? 'open' : ''}`}
        aria-hidden={!isOpen}
      >
        {mobileSections.map((section) => (
          <button
            key={section.id}
            type="button"
            className={`hamburger-item ${activeSection === section.id ? 'active' : ''}`}
            onClick={() => handleSelect(section.id)}
            title={section.title}
          >
            <div className={`nav-icon-img ${section.id}`} />
            <span>{section.title}</span>
          </button>
        ))}
      </div>
    </div>
  );
}

export default HamburgerMenu;
