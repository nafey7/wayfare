import axios from "axios";
import { isEmpty } from "lodash";

import { getSession, clearSession } from "services/service";

const AxiosDefault = async ({ method, data, url, contentType, isCustomer }) => {
  const APIENDPOINT = process.env.REACT_APP_API_END_POINT;
  const AxiosDefault = axios.create({
    baseURL: APIENDPOINT,
    headers: {
      "Content-Type": isEmpty(contentType) ? "application/json" : contentType,
      Accept: "application/json",
    },
  });

  AxiosDefault.interceptors.request.use(
    async function (config) {
      try {
        const { Authorization } = getSession();
        config.headers.Token = Authorization;
      } catch (err) {
        console.log("config error ======>", err);
      }
      return config;
    },
    function (error) {
      // Do something with request error
      return Promise.reject("promise reject ======>", error);
    }
  );

  // when your API throw Error
  AxiosDefault.interceptors.response.use(
    function (response) {
      return response;
    },
    async function (error) {
      if (error.response.status === 401) {
        try {
          //write here your code like clear sessin, cookie, and local storage here and redirect user landing page
          clearSession();
          window.location.replace("/");
          window.location = "/";
        } catch (err) {
          return err;
        }
      }
      return Promise.reject(error);
    }
  );
  return await AxiosDefault({
    method,
    data,
    url,
    contentType,
  });
};

export default AxiosDefault;
