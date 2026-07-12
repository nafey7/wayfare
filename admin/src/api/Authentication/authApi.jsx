import AxiosDefault from "services/AxiosDefault";

export const PostLogin = async (data) => {
  const response = await AxiosDefault({
    method: "POST",
    url: "/auth/login",
    data: data,
  });
  return response;
};
