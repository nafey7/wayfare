import AxiosDefault from "services/AxiosDefault";

export const GetUserInfo = async (data) => {
  const response = await AxiosDefault({
    method: "GET",
    url: "/user/get",
    data: data,
  });
  return response;
};

export const PasswordResetAPI = async (data) => {
  const response = await AxiosDefault({
    method: "POST",
    url: "/user/passwordReset",
    data: data,
  });
  return response;
};

export const GetMeInfo = async () => {
  const response = await AxiosDefault({
    method: "GET",
    url: `/user/me`,
  });
  return response;
};

export const GetAllUserAPI = async (data) => {
  const response = await AxiosDefault({
    method: "GET",
    url: "/user/getUsers",
    data: data,
  });
  return response;
};
