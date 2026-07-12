import AxiosDefault from "../../services/AxiosDefault";

const agentPromptsApi = {
  // Get all agent prompts
  getAllPrompts: async () => {
    try {
      const response = await AxiosDefault.get('/api/admin/agent-prompts');
      return response.data;
    } catch (error) {
      throw error;
    }
  },

  // Get prompt for specific agent
  getPromptByAgent: async (agentName) => {
    try {
      const response = await AxiosDefault.get(`/api/admin/agent-prompts/${agentName}`);
      return response.data;
    } catch (error) {
      throw error;
    }
  },

  // Create new agent prompt
  createPrompt: async (promptData) => {
    try {
      const response = await AxiosDefault.post('/api/admin/agent-prompts', promptData);
      return response.data;
    } catch (error) {
      throw error;
    }
  },

  // Update agent prompt
  updatePrompt: async (agentName, promptData) => {
    try {
      const response = await AxiosDefault.put(`/api/admin/agent-prompts/${agentName}`, promptData);
      return response.data;
    } catch (error) {
      throw error;
    }
  },

  // Initialize default prompts
  initializeDefaults: async () => {
    try {
      const response = await AxiosDefault.post('/api/admin/agent-prompts/initialize');
      return response.data;
    } catch (error) {
      throw error;
    }
  }
};

export default agentPromptsApi;