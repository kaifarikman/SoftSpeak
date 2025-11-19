import '../../css/components/HamburgerMenu.css';

function HamburgerMenu({ isOpen, toggleMenu }) {
  return (
    <button 
      className={`hamburger-menu ${isOpen ? 'open' : ''}`}
      onClick={toggleMenu}
      aria-label="Toggle menu"
    >
      <span className="hamburger-line"></span>
      <span className="hamburger-line"></span>
      <span className="hamburger-line"></span>
    </button>
  );
}

export default HamburgerMenu;

