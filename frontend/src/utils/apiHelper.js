




const isBanMessage = (data) => {
  if (!data || !data.detail) return false;
  const detail = String(data.detail).toLowerCase();
  return detail.includes('заблокирован') || detail.includes('забанен') || detail.includes('banned');
};



export const fetchWithBanCheck = async (url, options = {}) => {
  const response = await fetch(url, options);
  
  if (response.status === 403) {
    try {
      const clone = response.clone();
      const data = await clone.json();
      if (isBanMessage(data)) {
        window.dispatchEvent(new Event('userBanned'));
      }
    } catch (e) {

    }
  }
  
  return response;
};



export const checkBanStatus = async (response) => {
  if (response.status === 403) {
    try {
      const clone = response.clone();
      const data = await clone.json();
      if (isBanMessage(data)) {
        window.dispatchEvent(new Event('userBanned'));
        return true;
      }
    } catch (e) {

    }
  }
  return false;
};

