import AxiosDefault from "services/AxiosDefault";

export const GetRoles = async () => {
  const response = await AxiosDefault({
    method: "GET",
    url: "/roles/get",
  });
  return response;
};

export const CreateRole = async (data) => {
  const response = await AxiosDefault({
    method: "POST",
    url: "/roles/create",
    data
  });
  return response;
};

export const DeleteRoleAPI = async (data) => {
  const response = await AxiosDefault({
    method: "PATCH",
    url: "/roles/deleteRole",
    data: data,
  });
  return response;
};

export const StatusUpdateAPI = async (data) => {
  const response = await AxiosDefault({
    method: "PATCH",
    url: "/roles/statusUpdate",
    data: data,
  });
  return response;
};

export const UpdateRole = async (data) => {
  const response = await AxiosDefault({
    method: "PATCH",
    url: "/roles/update",
    data
  });
  return response;
};
