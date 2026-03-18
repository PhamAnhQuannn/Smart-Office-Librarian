import { cn } from "../../lib/utils";

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {}

export function Card({ className, children, ...props }: CardProps): JSX.Element {
  return (
    <div
      {...props}
      className={cn("rounded-2xl border border-slate-200 bg-white/80 shadow-sm backdrop-blur-sm", className)}
    >
      {children}
    </div>
  );
}

export function CardHeader({ className, children, ...props }: CardProps): JSX.Element {
  return (
    <div {...props} className={cn("border-b border-slate-200 px-6 py-4", className)}>
      {children}
    </div>
  );
}

export function CardBody({ className, children, ...props }: CardProps): JSX.Element {
  return (
    <div {...props} className={cn("px-6 py-4", className)}>
      {children}
    </div>
  );
}

export function CardFooter({ className, children, ...props }: CardProps): JSX.Element {
  return (
    <div {...props} className={cn("border-t border-slate-200 px-6 py-4", className)}>
      {children}
    </div>
  );
}
