import React from "react";
import { Link } from "react-router-dom";

export default function SmartLink({ to = "/", children, ...rest }) {
  if (/^(https?:|mailto:|tel:)/i.test(to)) {
    return <a href={to} target={to.startsWith("http") ? "_blank" : undefined} rel="noreferrer" {...rest}>{children}</a>;
  }
  return <Link to={to} {...rest}>{children}</Link>;
}
