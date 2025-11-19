import { Routes, Route } from 'react-router-dom';
import Landing from './pages/Landing';
import FirstStart from './pages/FirstStart';
import SignUp from './pages/SignUp';
import SignIn from './pages/SignIn';
import VerifyCode from './pages/VerifyCode';

import Messenger from './pages/Messenger';

function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/welcome" element={<FirstStart />} />
      <Route path="/signup" element={<SignUp />} />
      <Route path="/signin" element={<SignIn />} />
      <Route path="/verify" element={<VerifyCode />} />
      <Route path="/home" element={<Messenger />} />

    </Routes>
  );
}

export default App;
