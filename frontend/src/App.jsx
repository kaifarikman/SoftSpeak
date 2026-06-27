import { Routes, Route } from 'react-router-dom';
import Landing from './pages/Landing';
import SignUp from './pages/SignUp';
import SignIn from './pages/SignIn';
import VerifyCode from './pages/VerifyCode';

import Messenger from './pages/Messenger';
import Admin from './pages/Admin';
import PublicProfile from './pages/PublicProfile';

function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/signup" element={<SignUp />} />
      <Route path="/signin" element={<SignIn />} />
      <Route path="/verify" element={<VerifyCode />} />
      <Route path="/home" element={<Messenger />} />
      <Route path="/admin" element={<Admin />} />
      <Route path="/u/:nickname" element={<PublicProfile />} />

    </Routes>
  );
}

export default App;
