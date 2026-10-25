const crypto = require('crypto');
const mongoose = require('mongoose');
const bucketSchema = new mongoose.Schema(
  { _id: String, count: Number, expiresAt: Date },
  { versionKey: false },
);
bucketSchema.index({ expiresAt: 1 }, { expireAfterSeconds: 0 });
const Bucket = mongoose.models.RateBucket || mongoose.model('RateBucket', bucketSchema);
function rateLimit({ name, limit = 20, windowMs = 900000, account = false }) {
  return async (req, res, next) => {
    try {
      const subjects = [req.ip || 'unknown'];
      if (account && typeof req.body?.email === 'string')
        subjects.push('email:' + req.body.email.trim().toLowerCase());
      const now = Date.now();
      for (const subject of subjects) {
        const id = crypto
          .createHash('sha256')
          .update(`${name}:${Math.floor(now / windowMs)}:${subject}`)
          .digest('hex');
        let bucket;
        try {
          bucket = await Bucket.findOneAndUpdate(
            { _id: id },
            { $inc: { count: 1 }, $setOnInsert: { expiresAt: new Date(now + 2 * windowMs) } },
            { upsert: true, returnDocument: 'after' },
          );
        } catch (err) {
          if (err.code !== 11000) throw err;
          bucket = await Bucket.findOneAndUpdate(
            { _id: id },
            { $inc: { count: 1 } },
            { returnDocument: 'after' },
          );
        }
        if (bucket.count > limit) {
          res.set('Retry-After', String(Math.ceil((windowMs - (now % windowMs)) / 1000)));
          return res
            .status(429)
            .json({ success: false, message: 'Too many attempts. Please try again later.' });
        }
      }
      next();
    } catch {
      res
        .status(503)
        .json({ success: false, message: 'Request protection temporarily unavailable.' });
    }
  };
}
module.exports = { rateLimit };
