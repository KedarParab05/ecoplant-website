const axios = require('axios');

async function detectPlantDisease(imageBase64) {
  const apiKey = process.env.ROBOFLOW_API_KEY;
  const modelEndpoint = process.env.ROBOFLOW_PLANT_MODEL || 'plant-disease-detection/1';
  
  if (!apiKey || apiKey === 'your_roboflow_key') {
    throw new Error('Roboflow API key is not configured.');
  }

  try {
    const response = await axios({
      method: 'POST',
      url: `https://detect.roboflow.com/${modelEndpoint}?api_key=${apiKey}`,
      data: imageBase64,
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded'
      }
    });
    
    return response.data;
  } catch (error) {
    console.error('Roboflow Error (Plant):', error.response?.data || error.message);
    throw new Error('Failed to analyze plant image with Roboflow.');
  }
}

async function detectRoomObjects(imageBase64) {
  const apiKey = process.env.ROBOFLOW_API_KEY;
  const modelEndpoint = process.env.ROBOFLOW_ROOM_MODEL || 'room-object-detection/1';
  
  if (!apiKey || apiKey === 'your_roboflow_key') {
    throw new Error('Roboflow API key is not configured.');
  }

  try {
    const response = await axios({
      method: 'POST',
      url: `https://detect.roboflow.com/${modelEndpoint}?api_key=${apiKey}`,
      data: imageBase64,
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded'
      }
    });
    
    return response.data;
  } catch (error) {
    console.error('Roboflow Error (Room):', error.response?.data || error.message);
    throw new Error('Failed to analyze room image with Roboflow.');
  }
}

module.exports = {
  detectPlantDisease,
  detectRoomObjects
};
