/**
 * Placeholder blocks shown while data is loading.
 */

/**
 * Render one shimmering block.
 *
 * @param {{ className?: string }} props Component props.
 * @returns {JSX.Element} The block.
 */
function SkeletonLine({ className = '' }) {
  return <div className={`skeleton h-3 w-full ${className}`.trim()} />;
}

/**
 * Render a card-shaped loading placeholder.
 *
 * @param {{ count?: number, className?: string }} props Component props.
 * @returns {JSX.Element} The placeholder.
 */
export default function Skeleton({ count = 4, className = '' }) {
  return (
    <div className={className} aria-hidden="true">
      {Array.from({ length: count }, (_, index) => (
        <div key={index} className="card mb-4 space-y-3">
          <SkeletonLine className="w-1/3" />
          <SkeletonLine className="w-2/3" />
          <SkeletonLine className="w-1/2" />
        </div>
      ))}
    </div>
  );
}
